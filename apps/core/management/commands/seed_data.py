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

User = get_user_model()


class Command(BaseCommand):
    help = "Seeds the database with realistic test data including organizations, workspaces, teams, and entries"

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
            default=5,
            help='Number of users per organization (default: 5)'
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
                self.stdout.write("Clearing existing data...")
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
            # Clear entries first
            Entry.objects.all().delete()
            self.stdout.write("  - Cleared entries")
            
            # Clear workspace teams
            WorkspaceTeam.objects.all().delete()
            self.stdout.write("  - Cleared workspace teams")
            
            # Clear workspaces
            Workspace.objects.all().delete()
            self.stdout.write("  - Cleared workspaces")
            
            # Clear teams and team members
            TeamMember.objects.all().delete()
            Team.objects.all().delete()
            self.stdout.write("  - Cleared teams and team members")
            
            # Clear organization members
            OrganizationMember.objects.all().delete()
            self.stdout.write("  - Cleared organization members")
            
            # Clear organizations
            Organization.objects.all().delete()
            self.stdout.write("  - Cleared organizations")
            
            # Clear users (but keep superuser)
            CustomUser.objects.filter(is_superuser=False).delete()
            self.stdout.write("  - Cleared regular users")
            
            # Clear exchange rates
            OrganizationExchangeRate.objects.all().delete()
            WorkspaceExchangeRate.objects.all().delete()
            self.stdout.write("  - Cleared exchange rates")
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"Warning: Could not clear all data: {str(e)}")
            )

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
                # Create organization
                org = Organization.objects.create(
                    title=f"{faker.company()} {faker.company_suffix()}",
                    description=faker.text(max_nb_chars=200),
                    expense=Decimal('0.00'),
                    status=OrgStatusChoices.ACTIVE
                )
                
                # Create owner user
                owner_user = CustomUser.objects.create_user(
                    username=f"owner_{i}_{faker.user_name()}",
                    email=f"owner_{i}@{faker.domain_name()}",
                    password="password123",
                    status=UserStatusChoices.ACTIVE
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
                    # Select a team coordinator (not the owner)
                    available_members = [m for m in org_members if m != org.owner]
                    coordinator = random.choice(available_members) if available_members else org.owner
                    
                    team = Team.objects.create(
                        organization=org,
                        title=f"{faker.job()} Team {i+1}",
                        description=faker.text(max_nb_chars=150),
                        team_coordinator=coordinator,
                        created_by=org.owner
                    )
                    
                    # Create team member for coordinator
                    TeamMember.objects.create(
                        team=team,
                        organization_member=coordinator,
                        role=TeamMemberRole.SUBMITTER  # Using SUBMITTER since TEAM_COORDINATOR constant is commented out
                    )
                    
                    # Add other members to team
                    for member in org_members[:3]:  # Add first 3 members
                        if member != coordinator:
                            TeamMember.objects.create(
                                team=team,
                                organization_member=member,
                                role=TeamMemberRole.SUBMITTER
                            )
                    
                    teams.append(team)
                    self.stdout.write(f"  - Created team: {team.title} in {org.title}")
            
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
                    available_members = [m for m in org_members if m != org.owner]
                    workspace_admin = random.choice(available_members) if available_members else org.owner
                    
                    # Select operations reviewer (different from admin)
                    remaining_members = [m for m in available_members if m != workspace_admin]
                    operations_reviewer = random.choice(remaining_members) if remaining_members else org.owner
                    
                    # Generate realistic dates
                    start_date = date.today() - timedelta(days=random.randint(30, 180))
                    end_date = start_date + timedelta(days=random.randint(90, 365))
                    
                    workspace = Workspace.objects.create(
                        organization=org,
                        workspace_admin=workspace_admin,
                        operations_reviewer=operations_reviewer,
                        title=f"{faker.word().title()} Project {i+1}",
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
                    
                    # Determine submitter
                    if workspace_team and random.choice([True, False]):
                        # Team member submitter
                        team_members = list(workspace_team.team.members.all())
                        if team_members:
                            submitter = random.choice(team_members)
                            submitted_by_team_member = submitter
                            submitted_by_org_member = None
                        else:
                            continue
                    else:
                        # Organization member submitter
                        org_members = list(workspace.organization.members.all())
                        submitter = random.choice(org_members)
                        submitted_by_org_member = submitter
                        submitted_by_team_member = None
                    
                    # Generate realistic dates
                    occurred_at = workspace.start_date + timedelta(
                        days=random.randint(0, (workspace.end_date - workspace.start_date).days)
                    )
                    
                    # Create entry
                    entry = Entry.objects.create(
                        entry_type=entry_type,
                        description=faker.sentence(nb_words=6),
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
                    # Create multiple rates for different dates
                    for i in range(3):
                        effective_date = date.today() - timedelta(days=i * 30)
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
                    # Create multiple rates for different dates
                    for i in range(2):
                        effective_date = workspace.start_date + timedelta(days=i * 45)
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
