import random
import uuid
from datetime import date, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from faker import Faker

from apps.accounts.models import CustomUser
from apps.organizations.models import Organization, OrganizationMember, OrganizationExchangeRate
from apps.workspaces.models import Workspace, WorkspaceTeam, WorkspaceExchangeRate
from apps.teams.models import Team, TeamMember
from apps.entries.models import Entry
from apps.currencies.models import Currency
from apps.entries.constants import EntryType, EntryStatus
from apps.teams.constants import TeamMemberRole
from apps.accounts.constants import StatusChoices as UserStatusChoices
from apps.organizations.constants import StatusChoices as OrgStatusChoices
from apps.workspaces.constants import StatusChoices as WorkspaceStatusChoices

# Import Django and guardian modules for permission assignment
from django.contrib.auth.models import Group
from guardian.shortcuts import assign_perm
from apps.core.roles import get_permissions_for_role

# Import permission assignment functions
from apps.workspaces.permissions import assign_workspace_permissions, assign_workspace_team_permissions
from apps.teams.permissions import assign_team_permissions

User = get_user_model()


class Command(BaseCommand):
    help = "Seeds the database with realistic test data including organizations, workspaces, teams, and entries"
    
    """
    ROLE SEPARATION STRATEGY:
    - Each organization gets 10+ users by default
    - Organization Owner: 1 user (full org permissions)
    - Workspace Admin: 1 user per workspace (workspace management)
    - Operations Reviewer: 1 user per workspace (review/export permissions)
    - Team Coordinator: 1 user per team (team management)
    - Regular Members: Remaining users (entry submission, basic access)
    
    This ensures no single user has conflicting roles and proper separation of duties.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            '--organizations',
            type=int,
            default=3,
            help='Number of organizations to create (default: 3)'
        )
        parser.add_argument(
            '--workspaces-per-org',
            type=int,
            default=2,
            help='Number of workspaces per organization (default: 2)'
        )
        parser.add_argument(
            '--teams-per-org',
            type=int,
            default=3,
            help='Number of teams per organization (default: 3)'
        )
        parser.add_argument(
            '--users-per-org',
            type=int,
            default=10,
            help='Number of users per organization (default: 10)'
        )
        parser.add_argument(
            '--entries-per-workspace',
            type=int,
            default=10,
            help='Number of entries per workspace (default: 10)'
        )
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing data before seeding'
        )

    def handle(self, *args, **options):
        try:
            if options['clear_existing']:
                self.stdout.write(
                    self.style.WARNING(
                        "⚠️  WARNING: This will DELETE ALL existing data from the database!\n"
                        "This action cannot be undone. Are you sure you want to continue?"
                    )
                )
                
                # Ask for confirmation
                confirm = input("Type 'yes' to confirm: ")
                if confirm.lower() != 'yes':
                    self.stdout.write(
                        self.style.ERROR("❌ Database clearing cancelled by user.")
                    )
                    return
                
                self.stdout.write("🗑️  Clearing existing data...")
                self.clear_existing_data()

            self.stdout.write("Starting data seeding process...")
            
            # Create currencies first
            self.create_currencies()
            
            # Create organizations and their members
            organizations = self.create_organizations(
                count=options['organizations'],
                users_per_org=options['users_per_org']
            )
            
            # Create teams for each organization
            teams = self.create_teams(
                organizations=organizations,
                teams_per_org=options['teams_per_org']
            )
            
            # Create workspaces for each organization
            workspaces = self.create_workspaces(
                organizations=organizations,
                workspaces_per_org=options['workspaces_per_org']
            )
            
            # Create workspace teams
            workspace_teams = self.create_workspace_teams(
                workspaces=workspaces,
                teams=teams
            )
            
            # Create entries
            self.create_entries(
                workspaces=workspaces,
                workspace_teams=workspace_teams,
                entries_per_workspace=options['entries_per_workspace']
            )
            
            # Create exchange rates
            self.create_exchange_rates(organizations, workspaces)
            
            # Resolve any role conflicts and ensure proper role separation
            self.resolve_role_conflicts(organizations, workspaces, teams)
            
            # Show role distribution summary
            self.stdout.write("\n" + "="*60)
            self.stdout.write("ROLE DISTRIBUTION SUMMARY:")
            self.stdout.write("="*60)
            
            for org in organizations:
                self.stdout.write(f"\n📁 Organization: {org.title}")
                self.stdout.write(f"   👑 Owner: {org.owner.user.username} ({org.owner.user.email})")
                
                # Show workspace roles
                org_workspaces = [w for w in workspaces if w.organization == org]
                for ws in org_workspaces:
                    self.stdout.write(f"   🏢 Workspace: {ws.title}")
                    self.stdout.write(f"      👨‍💼 Admin: {ws.workspace_admin.user.username}")
                    self.stdout.write(f"      👁️  Reviewer: {ws.operations_reviewer.user.username}")
                
                # Show team roles
                org_teams = [t for t in teams if t.organization == org]
                for team in org_teams:
                    self.stdout.write(f"   👥 Team: {team.title}")
                    self.stdout.write(f"      🎯 Coordinator: {team.team_coordinator.user.username}")
                
                # Show regular members
                regular_members = [m for m in org.members.all() if m != org.owner and 
                                 m not in [ws.workspace_admin for ws in org_workspaces] and
                                 m not in [ws.operations_reviewer for ws in org_workspaces] and
                                 m not in [t.team_coordinator for t in org_teams]]
                
                if regular_members:
                    self.stdout.write(f"   👤 Regular Members: {', '.join([m.user.username for m in regular_members[:5]])}")
                    if len(regular_members) > 5:
                        self.stdout.write(f"      ... and {len(regular_members) - 5} more")
            
            self.stdout.write("\n" + "="*60)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully seeded database with:\n"
                    f"- {len(organizations)} organizations\n"
                    f"- {len(workspaces)} workspaces\n"
                    f"- {len(teams)} teams\n"
                    f"- {len(workspace_teams)} workspace teams\n"
                    f"- {Entry.objects.count()} entries\n"
                    f"- {Currency.objects.count()} currencies"
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error seeding data: {str(e)}")
            )
            raise

    def clear_existing_data(self):
        """Clear existing data in the correct order to respect foreign key constraints."""
        try:
            self.stdout.write("  🗑️  Clearing database...")
            
            # Import signals to disable them temporarily
            from django.db.models.signals import post_delete
            from apps.entries.signals import revert_remittance_on_entry_delete
            
            # Temporarily disconnect the problematic signal
            post_delete.disconnect(revert_remittance_on_entry_delete, sender=Entry)
            
            try:
                # Clear entries first (most dependent)
                entries_count = Entry.objects.count()
                Entry.objects.all().delete()
                self.stdout.write(f"    ✅ Cleared {entries_count} entries")
                
                # Clear workspace teams
                ws_teams_count = WorkspaceTeam.objects.count()
                WorkspaceTeam.objects.all().delete()
                self.stdout.write(f"    ✅ Cleared {ws_teams_count} workspace teams")
                
                # Clear workspaces
                workspaces_count = Workspace.objects.count()
                Workspace.objects.all().delete()
                self.stdout.write(f"    ✅ Cleared {workspaces_count} workspaces")
                
                # Clear teams and team members
                team_members_count = TeamMember.objects.count()
                teams_count = Team.objects.count()
                TeamMember.objects.all().delete()
                Team.objects.all().delete()
                self.stdout.write(f"    ✅ Cleared {team_members_count} team members and {teams_count} teams")
                
                # Clear organization members
                org_members_count = OrganizationMember.objects.count()
                OrganizationMember.objects.all().delete()
                self.stdout.write(f"    ✅ Cleared {org_members_count} organization members")
                
                # Clear organizations
                orgs_count = Organization.objects.count()
                Organization.objects.all().delete()
                self.stdout.write(f"    ✅ Cleared {orgs_count} organizations")
                
                # Clear users (but keep superuser)
                users_count = CustomUser.objects.filter(is_superuser=False).count()
                CustomUser.objects.filter(is_superuser=False).delete()
                self.stdout.write(f"    ✅ Cleared {users_count} regular users")
                
                # Clear exchange rates
                org_rates_count = OrganizationExchangeRate.objects.count()
                ws_rates_count = WorkspaceExchangeRate.objects.count()
                OrganizationExchangeRate.objects.all().delete()
                WorkspaceExchangeRate.objects.all().delete()
                self.stdout.write(f"    ✅ Cleared {org_rates_count} organization and {ws_rates_count} workspace exchange rates")
                
                self.stdout.write("  🎉 Database cleared successfully!")
                
            finally:
                # Reconnect the signal
                post_delete.connect(revert_remittance_on_entry_delete, sender=Entry)
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error clearing database: {str(e)}")
            )
            raise

    def create_currencies(self):
        """Create common currencies."""
        try:
            currencies_data = [
                {'code': 'USD', 'name': 'US Dollar'},
                {'code': 'EUR', 'name': 'Euro'},
                {'code': 'GBP', 'name': 'British Pound'},
                {'code': 'JPY', 'name': 'Japanese Yen'},
                {'code': 'CAD', 'name': 'Canadian Dollar'},
                {'code': 'AUD', 'name': 'Australian Dollar'},
                {'code': 'CHF', 'name': 'Swiss Franc'},
                {'code': 'CNY', 'name': 'Chinese Yuan'},
            ]
            
            for currency_data in currencies_data:
                Currency.objects.get_or_create(
                    code=currency_data['code'],
                    defaults={'name': currency_data['name']}
                )
            
            self.stdout.write(f"  - Created {len(currencies_data)} currencies")
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"Warning: Could not create currencies: {str(e)}")
            )

    def create_organizations(self, count, users_per_org):
        """Create organizations with owners and members."""
        try:
            faker = Faker()
            organizations = []
            
            for i in range(count):
                # Create owner user first
                owner_user = CustomUser.objects.create_user(
                    username=f"owner_{i}_{faker.user_name()}",
                    email=f"owner_{i}@{faker.domain_name()}",
                    password="password123",
                    status=UserStatusChoices.ACTIVE
                )
                
                # Create organization with NGO-themed names
                ngo_names = [
                    f"{faker.word().title()} Foundation",
                    f"{faker.word().title()} Initiative",
                    f"{faker.word().title()} Alliance",
                    f"{faker.word().title()} Network",
                    f"{faker.word().title()} Coalition",
                    f"{faker.word().title()} Partnership",
                    f"{faker.word().title()} Organization",
                    f"{faker.word().title()} Association",
                    f"{faker.word().title()} Council",
                    f"{faker.word().title()} Trust",
                    f"{faker.word().title()} Society",
                    f"{faker.word().title()} Group",
                    f"{faker.word().title()} Movement",
                    f"{faker.word().title()} Community",
                    f"{faker.word().title()} Collective",
                    f"{faker.word().title()} Institute",
                    f"{faker.word().title()} Center",
                    f"{faker.word().title()} Agency",
                    f"{faker.word().title()} Service",
                    f"{faker.word().title()} Program",
                    f"{faker.word().title()} Project",
                    f"{faker.word().title()} Mission",
                    f"{faker.word().title()} Vision",
                    f"{faker.word().title()} Action",
                    f"{faker.word().title()} Support",
                    f"{faker.word().title()} Development",
                    f"{faker.word().title()} Relief",
                    f"{faker.word().title()} Aid",
                    f"{faker.word().title()} Care",
                    f"{faker.word().title()} Help",
                    f"{faker.word().title()} Hope",
                    f"{faker.word().title()} Future",
                    f"{faker.word().title()} Progress",
                    f"{faker.word().title()} Change",
                    f"{faker.word().title()} Impact",
                    f"{faker.word().title()} Solutions",
                    f"{faker.word().title()} Partners",
                    f"{faker.word().title()} United",
                    f"{faker.word().title()} Global",
                    f"{faker.word().title()} International",
                    f"{faker.word().title()} Regional",
                    f"{faker.word().title()} Local",
                    f"{faker.word().title()} National"
                ]
                
                org_name = random.choice(ngo_names)
                # Ensure unique organization name by checking if it exists
                counter = 1
                original_name = org_name
                while Organization.objects.filter(title=org_name).exists():
                    org_name = f"{original_name} {counter}"
                    counter += 1
                
                org = Organization.objects.create(
                    title=org_name,
                    description=faker.text(max_nb_chars=200),
                    expense=Decimal('0.00'),
                    status=OrgStatusChoices.ACTIVE
                )
                
                # Create organization member for owner
                owner_member = OrganizationMember.objects.create(
                    organization=org,
                    user=owner_user,
                    is_active=True
                )
                
                # Set owner
                org.owner = owner_member
                org.save()
                
                # Manually assign organization permissions (similar to create_organization_with_owner)
                try:
                    # Create org owner group
                    org_owner_group, _ = Group.objects.get_or_create(
                        name=f"Org Owner - {org.organization_id}"
                    )
                    
                    # Get permissions for org owner role
                    org_owner_permissions = get_permissions_for_role("ORG_OWNER")
                    
                    # Assign permissions to the org owner group
                    for perm in org_owner_permissions:
                        if "workspace_currency" not in perm:
                            assign_perm(perm, org_owner_group, org)
                    
                    # Assign the org owner group to the user
                    org_owner_group.user_set.add(owner_user)
                    
                    self.stdout.write(f"    - Assigned organization permissions for {org.title}")
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f"    - Warning: Could not assign organization permissions: {str(e)}")
                    )
                
                # Create additional members
                for j in range(users_per_org - 1):
                    member_user = CustomUser.objects.create_user(
                        username=f"member_{i}_{j}_{faker.user_name()}",
                        email=f"member_{i}_{j}@{faker.domain_name()}",
                        password="password123",
                        status=UserStatusChoices.ACTIVE
                    )
                    
                    OrganizationMember.objects.create(
                        organization=org,
                        user=member_user,
                        is_active=True
                    )
                
                organizations.append(org)
                self.stdout.write(f"  - Created organization: {org.title}")
            
            return organizations
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error creating organizations: {str(e)}")
            )
            raise

    def create_teams(self, organizations, teams_per_org):
        """Create teams for each organization."""
        try:
            faker = Faker()
            teams = []
            
            for org in organizations:
                org_members = list(org.members.all())
                
                for i in range(teams_per_org):
                    # Select a team coordinator (not the owner, and not already assigned to other roles)
                    # We'll check for conflicts later when we have all the data
                    available_members = [m for m in org_members if m != org.owner]
                    
                    # Try to avoid members that might be used in other roles
                    # For now, just pick from available members
                    coordinator = random.choice(available_members) if available_members else org.owner
                    
                    # Note: Team coordinators get TEAM_COORDINATOR role, not SUBMITTER role
                    
                    # Create NGO-themed team names with more variety
                    team_types = [
                        "Program Management",
                        "Field Operations", 
                        "Monitoring & Evaluation",
                        "Finance & Administration",
                        "Communications",
                        "Partnership Development",
                        "Research & Policy",
                        "Capacity Building",
                        "Advocacy & Outreach",
                        "Emergency Response",
                        "Technical Support",
                        "Community Engagement",
                        "Logistics & Procurement",
                        "Training & Development",
                        "Impact Assessment",
                        "Health Services",
                        "Education Support",
                        "Environmental Protection",
                        "Women's Empowerment",
                        "Youth Development",
                        "Disaster Management",
                        "Food Security",
                        "Water & Sanitation",
                        "Energy Solutions",
                        "Microfinance",
                        "Human Rights",
                        "Refugee Support",
                        "Rural Development",
                        "Urban Planning",
                        "Cultural Preservation"
                    ]
                    
                    # Use faker to generate more unique team names
                    team_name = f"{faker.word().title()} {random.choice(team_types)}"
                    # Ensure unique team name by checking if it exists
                    counter = 1
                    original_name = team_name
                    while Team.objects.filter(organization=org, title=team_name).exists():
                        team_name = f"{original_name} {counter}"
                        counter += 1
                    team = Team.objects.create(
                        organization=org,
                        title=team_name,
                        description=faker.text(max_nb_chars=150),
                        team_coordinator=coordinator,
                        created_by=org.owner
                    )
                    
                    # Create team member for coordinator with proper role
                    TeamMember.objects.create(
                        team=team,
                        organization_member=coordinator,
                        role=TeamMemberRole.TEAM_COORDINATOR
                    )
                    
                    # Add other members to team (avoiding coordinators from other teams)
                    other_team_coordinators = [t.team_coordinator for t in teams]
                    # Filter out current coordinator and other team coordinators
                    available_team_members = [
                        m for m in org_members[:5] 
                        if m != coordinator and m not in other_team_coordinators
                    ]
                    
                    for member in available_team_members:
                        TeamMember.objects.create(
                            team=team,
                            organization_member=member,
                            role=TeamMemberRole.SUBMITTER
                        )
                    
                    teams.append(team)
                    self.stdout.write(f"  - Created team: {team.title} in {org.title}")
                    
                    # Assign team permissions
                    try:
                        assign_team_permissions(team)
                        self.stdout.write(f"    - Assigned team permissions for {team.title}")
                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(f"    - Warning: Could not assign team permissions: {str(e)}")
                        )
            
            return teams
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error creating teams: {str(e)}")
            )
            raise

    def create_workspaces(self, organizations, workspaces_per_org):
        """Create workspaces for each organization."""
        try:
            faker = Faker()
            workspaces = []
            
            for org in organizations:
                org_members = list(org.members.all())
                
                for i in range(workspaces_per_org):
                    # Select workspace admin (not the owner)
                    available_admin_members = [m for m in org_members if m != org.owner]
                    workspace_admin = random.choice(available_admin_members) if available_admin_members else org.owner
                    
                    # Select operations reviewer (different from admin)
                    remaining_members = [m for m in org_members if m != org.owner and m != workspace_admin]
                    if not remaining_members:
                        remaining_members = [m for m in org_members if m != org.owner]
                    
                    operations_reviewer = random.choice(remaining_members) if remaining_members else org.owner
                    
                    # Generate realistic dates (all in the past)
                    start_date = date.today() - timedelta(days=random.randint(180, 365))  # 6-12 months ago
                    end_date = date.today() + timedelta(days=random.randint(1, 7))      # 1-7 days from today
                    
                    # Create NGO-themed workspace names with more variety
                    project_types = [
                        "Education Program",
                        "Healthcare Initiative", 
                        "Community Development",
                        "Environmental Conservation",
                        "Women Empowerment",
                        "Youth Development",
                        "Disaster Relief",
                        "Food Security",
                        "Clean Water Project",
                        "Renewable Energy",
                        "Microfinance Program",
                        "Human Rights Advocacy",
                        "Refugee Support",
                        "Rural Development",
                        "Urban Renewal",
                        "Child Protection",
                        "Elderly Care",
                        "Disability Support",
                        "Mental Health",
                        "Nutrition Program",
                        "Hygiene Education",
                        "Skills Training",
                        "Job Creation",
                        "Market Access",
                        "Technology Transfer",
                        "Climate Adaptation",
                        "Biodiversity Conservation",
                        "Sustainable Agriculture",
                        "Forest Management",
                        "Marine Protection",
                        "Waste Management",
                        "Transportation",
                        "Housing Support",
                        "Legal Aid",
                        "Gender Equality",
                        "Peace Building",
                        "Conflict Resolution"
                    ]
                    
                    # Use faker to generate more unique project names
                    project_name = f"{faker.word().title()} {random.choice(project_types)}"
                    # Ensure unique project name by checking if it exists
                    counter = 1
                    original_name = project_name
                    while Workspace.objects.filter(organization=org, title=project_name).exists():
                        project_name = f"{original_name} {counter}"
                        counter += 1
                    workspace = Workspace.objects.create(
                        organization=org,
                        workspace_admin=workspace_admin,
                        operations_reviewer=operations_reviewer,
                        title=project_name,
                        description=faker.text(max_nb_chars=200),
                        created_by=org.owner,
                        status=WorkspaceStatusChoices.ACTIVE,
                        remittance_rate=Decimal(random.randint(80, 95)),
                        start_date=start_date,
                        end_date=end_date,
                        expense=Decimal('0.00')
                    )
                    
                    workspaces.append(workspace)
                    self.stdout.write(f"  - Created workspace: {workspace.title} in {org.title}")
                    
                    # Assign workspace permissions
                    try:
                        assign_workspace_permissions(workspace, request_user=org.owner.user)
                        self.stdout.write(f"    - Assigned workspace permissions for {workspace.title}")
                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(f"    - Warning: Could not assign workspace permissions: {str(e)}")
                        )
            
            return workspaces
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error creating workspaces: {str(e)}")
            )
            raise

    def create_workspace_teams(self, workspaces, teams):
        """Create workspace teams linking workspaces and teams."""
        try:
            workspace_teams = []
            
            for workspace in workspaces:
                # Get teams from the same organization
                org_teams = [t for t in teams if t.organization == workspace.organization]
                 
                # Assign 1-3 teams to each workspace
                num_teams = min(random.randint(1, 3), len(org_teams))
                selected_teams = random.sample(org_teams, num_teams)
                
                for team in selected_teams:
                    # Sometimes use custom remittance rate
                    custom_rate = None
                    if random.choice([True, False]):
                        custom_rate = Decimal(random.randint(75, 100))
                    
                    workspace_team = WorkspaceTeam.objects.create(
                        team=team,
                        workspace=workspace,
                        custom_remittance_rate=custom_rate
                    )
                    
                    # Assign workspace team permissions
                    try:
                        assign_workspace_team_permissions(workspace_team, request_user=workspace.organization.owner.user)
                        self.stdout.write(f"    - Assigned workspace team permissions for {team.title} in {workspace.title}")
                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(f"    - Warning: Could not assign workspace team permissions: {str(e)}")
                        )
                    
                    workspace_teams.append(workspace_team)
                    self.stdout.write(f"  - Linked team {team.title} to workspace {workspace.title}")
            
            return workspace_teams
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error creating workspace teams: {str(e)}")
            )
            raise

    def create_entries(self, workspaces, workspace_teams, entries_per_workspace):
        """Create entries for each workspace."""
        try:
            faker = Faker()
            currencies = list(Currency.objects.all())
            entry_types = [choice[0] for choice in EntryType.choices]
            entry_statuses = [choice[0] for choice in EntryStatus.choices]
            
            for workspace in workspaces:
                # Get workspace teams for this workspace
                ws_teams = [wt for wt in workspace_teams if wt.workspace == workspace]
                
                for i in range(entries_per_workspace):
                    # Determine entry type and context
                    entry_type = random.choice(entry_types)
                    
                    # For certain entry types, we need workspace_team
                    workspace_team = None
                    if entry_type in [EntryType.INCOME, EntryType.DISBURSEMENT, EntryType.REMITTANCE]:
                        if ws_teams:
                            workspace_team = random.choice(ws_teams)
                        else:
                            continue  # Skip if no workspace teams
                    
                    # Generate realistic amounts
                    if entry_type == EntryType.INCOME:
                        amount = Decimal(random.randint(1000, 50000)) / 100
                    elif entry_type == EntryType.DISBURSEMENT:
                        amount = Decimal(random.randint(500, 10000)) / 100
                    else: # EntryType.REMITTANCE
                        amount = Decimal(random.randint(100, 5000)) / 100
                    
                    # Select currency and generate exchange rate
                    currency = random.choice(currencies)
                    exchange_rate = Decimal(random.randint(80, 120)) / 100
                    
                    # Determine submitter (avoiding users with admin/reviewer roles for better distribution)
                    if workspace_team and random.choice([True, False]):
                        # Team member submitter
                        team_members = list(workspace_team.team.members.all())
                        if team_members:
                            # Prefer regular team members over coordinators
                            regular_members = [tm for tm in team_members if tm != workspace_team.team.team_coordinator]
                            if regular_members:
                                submitter = random.choice(regular_members)
                            else:
                                submitter = random.choice(team_members)
                            
                            submitted_by_team_member = submitter
                            submitted_by_org_member = None
                        else:
                            continue
                    else:
                        # Organization member submitter (avoiding admin roles)
                        org_members = list(workspace.organization.members.all())
                        # Filter out users with admin roles
                        admin_users = [workspace.workspace_admin, workspace.operations_reviewer]
                        available_submitters = [m for m in org_members if m not in admin_users]
                        
                        if available_submitters:
                            submitter = random.choice(available_submitters)
                        else:
                            submitter = random.choice(org_members)
                        
                        submitted_by_org_member = submitter
                        submitted_by_team_member = None
                    
                    # Generate realistic dates
                    occurred_at = workspace.start_date + timedelta(
                        days=random.randint(0, (workspace.end_date - workspace.start_date).days)
                    )
                    
                    # Create NGO-themed entry descriptions
                    ngo_activities = [
                        "Community workshop materials and supplies",
                        "Field staff transportation and accommodation",
                        "Training program venue rental",
                        "Medical supplies for health clinic",
                        "School supplies for education program",
                        "Agricultural tools and seeds distribution",
                        "Clean water project equipment",
                        "Emergency relief food distribution",
                        "Women's empowerment workshop",
                        "Youth skills training materials",
                        "Environmental awareness campaign",
                        "Microfinance loan disbursement",
                        "Human rights documentation",
                        "Refugee support services",
                        "Rural infrastructure development"
                    ]
                    
                    entry_description = random.choice(ngo_activities)
                    
                    # Create entry
                    entry = Entry.objects.create(
                        entry_type=entry_type,
                        description=entry_description,
                        organization=workspace.organization,
                        workspace=workspace,
                        workspace_team=workspace_team,
                        amount=amount,
                        occurred_at=occurred_at,
                        currency=currency,
                        exchange_rate_used=exchange_rate,
                        org_exchange_rate_ref=None,  # Will be set by exchange rate creation
                        workspace_exchange_rate_ref=None,  # Will be set by exchange rate creation
                        submitted_by_org_member=submitted_by_org_member,
                        submitted_by_team_member=submitted_by_team_member,
                        status=random.choice(entry_statuses),
                        is_flagged=random.choice([True, False]) if random.random() < 0.1 else False
                    )
                    
                    # Update workspace expense
                    workspace.expense += entry.converted_amount
                    workspace.save()
                    
                    # Update organization expense
                    workspace.organization.expense += entry.converted_amount
                    workspace.organization.save()
                    
                self.stdout.write(f"  - Created {entries_per_workspace} entries for workspace {workspace.title}")
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error creating entries: {str(e)}")
            )
            raise

    def create_exchange_rates(self, organizations, workspaces):
        """Create exchange rates for organizations and workspaces."""
        try:
            currencies = list(Currency.objects.all())
            
            # Create organization exchange rates
            for org in organizations:
                for currency in currencies[:3]:  # First 3 currencies
                    # Create multiple rates for different dates (all in the past)
                    for i in range(3):
                        effective_date = date.today() - timedelta(days=random.randint(30, 180))  # 1-6 months ago
                        rate = Decimal(random.randint(80, 120)) / 100
                        
                        OrganizationExchangeRate.objects.create(
                            organization=org,
                            currency=currency,
                            rate=rate,
                            effective_date=effective_date,
                            added_by=org.owner,
                            note=f"Seed data exchange rate for {currency.code}"
                        )
            
            # Create workspace exchange rates
            for workspace in workspaces:
                for currency in currencies[:2]:  # First 2 currencies
                    # Create multiple rates for different dates (all in the past)
                    for i in range(2):
                        # Generate dates within the workspace period, ensuring they're in the past
                        days_offset = random.randint(0, min(180, (date.today() - workspace.start_date).days))
                        effective_date = workspace.start_date + timedelta(days=days_offset)
                        rate = Decimal(random.randint(80, 120)) / 100
                        
                        WorkspaceExchangeRate.objects.create(
                            workspace=workspace,
                            currency=currency,
                            rate=rate,
                            effective_date=effective_date,
                            added_by=workspace.workspace_admin or workspace.organization.owner,
                            note=f"Seed data workspace exchange rate for {currency.code}",
                            is_approved=random.choice([True, False]),
                            approved_by=workspace.operations_reviewer if random.choice([True, False]) else None
                        )
            
            self.stdout.write("  - Created exchange rates for organizations and workspaces")
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"Warning: Could not create exchange rates: {str(e)}")
            )

    def resolve_role_conflicts(self, organizations, workspaces, teams):
        """Resolve role conflicts and ensure proper role separation."""
        try:
            self.stdout.write("\n🔧 Resolving role conflicts...")
            
            for org in organizations:
                org_members = list(org.members.all())
                org_workspaces = [w for w in workspaces if w.organization == org]
                org_teams = [t for t in teams if t.organization == org]
                
                # Collect all assigned roles
                assigned_roles = set()
                assigned_roles.add(org.owner)  # Owner
                
                # Workspace roles
                for ws in org_workspaces:
                    assigned_roles.add(ws.workspace_admin)
                    assigned_roles.add(ws.operations_reviewer)
                
                # Team roles
                for team in org_teams:
                    assigned_roles.add(team.team_coordinator)
                
                # Find members with multiple roles
                conflicts = []
                for member in org_members:
                    role_count = 0
                    roles = []
                    
                    if member == org.owner:
                        role_count += 1
                        roles.append("Owner")
                    
                    for ws in org_workspaces:
                        if member == ws.workspace_admin:
                            role_count += 1
                            roles.append(f"Workspace Admin ({ws.title})")
                        if member == ws.operations_reviewer:
                            role_count += 1
                            roles.append(f"Operations Reviewer ({ws.title})")
                    
                    for team in org_teams:
                        if member == team.team_coordinator:
                            role_count += 1
                            roles.append(f"Team Coordinator ({team.title})")
                    
                    if role_count > 1:
                        conflicts.append((member, roles))
                
                # Report conflicts
                if conflicts:
                    self.stdout.write(f"  ⚠️  Found role conflicts in {org.title}:")
                    for member, roles in conflicts:
                        self.stdout.write(f"     {member.user.username}: {', '.join(roles)}")
                else:
                    self.stdout.write(f"  ✅ No role conflicts in {org.title}")
            
            self.stdout.write("  ✅ Role conflict resolution completed")
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"  ⚠️  Warning: Could not resolve role conflicts: {str(e)}")
            )
