# Core Management Commands

This directory contains Django management commands for the Fyndora application's core functionality.

## 📋 Available Commands

### 1. `seed_data` - Database Seeding Command

Populates your database with realistic test data for development, testing, and demonstration purposes.

## 🚀 Quick Start

### Basic Usage
```bash
# Seed with default settings (keeps existing data)
# Default: 3 orgs, 6 workspaces, 9 teams, 30 users, 60 entries
uv run manage.py seed_data #

# Clear existing data and seed fresh
# Default: 3 orgs, 6 workspaces, 9 teams, 30 users, 60 entries
uv run manage.py seed_data --clear-existing

# Customize data amounts
# too much data will cause the command to take a long time to run
uv run manage.py seed_data --organizations 5 --workspaces-per-org 10 --teams-per-org 15 --users-per-org 20 --entries-per-workspace 30
```

## ⚙️ Command Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--organizations` | int | 3 | Number of organizations to create |
| `--workspaces-per-org` | int | 2 | Workspaces per organization |
| `--teams-per-org` | int | 3 | Teams per organization |
| `--users-per-org` | int | 20 | Users per organization |
| `--entries-per-workspace` | int | 100 | Entries per workspace |
| `--clear-existing` | flag | False | Clear all existing data before seeding |

## 📊 Default Data Counts

When using default settings, the command creates:

| Data Type | Count | Calculation |
|-----------|-------|-------------|
| **Organizations** | 3 | Default value |
| **Workspaces** | 6 | 3 orgs × 2 per org |
| **Teams** | 9 | 3 orgs × 3 per org |
| **Users** | 60 | 3 orgs × 20 per org |
| **Entries** | 600 | 6 workspaces × 100 per workspace |
| **Workspace Teams** | 6-18 | Random: 1-3 teams per workspace |
| **Currencies** | 8 | Hardcoded currency list |
| **Exchange Rates** | 51 | (3 orgs × 3 currencies × 3 dates) + (6 workspaces × 2 currencies × 2 dates) |

## 🔒 Safety Features

### Confirmation Required
When using `--clear-existing`, the command requires explicit confirmation:

```
⚠️  WARNING: This will DELETE ALL existing data from the database!
This action cannot be undone. Are you sure you want to continue?
Type 'yes' to confirm: yes
```

**Only typing "yes" will proceed with data deletion.**

### Signal Handling
- Temporarily disables Django signals during database clearing
- Prevents signal-related errors during bulk deletion
- Automatically reconnects signals after completion

## 📊 Data Structure Created

### Organizations
- **Naming**: NGO-themed names (e.g., "Azure Foundation", "Crimson Initiative")
- **Uniqueness**: Automatic conflict resolution for duplicate names
- **Users**: 20+ users per organization by default
- **Roles**: Organization owner with full permissions

### Workspaces
- **Naming**: Project-based names (e.g., "Azure Education Program")
- **Dates**: Start dates 6-12 months ago, end dates 1-7 days from today
- **Roles**: Workspace admin and operations reviewer
- **Rates**: Random remittance rates (80-95%)

### Teams
- **Naming**: Functional team names (e.g., "Azure Program Management")
- **Roles**: Team coordinator assigned with `TEAM_COORDINATOR` role
- **Members**: Multiple team members with `SUBMITTER` role
- **Role Separation**: Coordinators cannot be submitters of the same team
- **Types**: 30+ different team types (Health Services, Education Support, etc.)

### Users
- **Creation**: Realistic usernames and email addresses using Faker
- **Password**: All users get "password123" for easy testing
- **Role Assignment**: Automatic role distribution with conflict resolution
- **Permissions**: Proper permission assignment based on roles

### Entries
- **Types**: Income, Disbursement, Remittance, Workspace Expense, and Organization Expense
- **Validation**: 
  - Workspace Expense entries: Only workspace admin of that specific workspace can create
  - Organization Expense entries: Only organization owners can create
  - Team-based entries: Team members can create
- **Submitters**: Team members or organization members based on entry type
- **Amounts**: Realistic amounts based on entry type
- **Dates**: Within workspace date ranges
- **Attachments**: Random flagging for testing purposes

### Exchange Rates
- **Organization**: 3 currencies × 3 dates per organization
- **Workspace**: 2 currencies × 2 dates per workspace
- **Rates**: Random rates (80-120% of base)
- **Approval**: Some workspace rates require approval

### Workspace Teams
- **Assignment**: Random assignment of 1-3 teams per workspace
- **Variability**: Not every workspace gets all teams (more realistic)
- **Custom Rates**: Sometimes custom remittance rates are applied

## 🎯 Use Cases

### Development Environment
```bash
# Fresh start for development
uv run manage.py seed_data --clear-existing

# Add more test data
uv run manage.py seed_data --organizations 2
```

### Testing
```bash
# Minimal data for unit tests
uv run manage.py seed_data --organizations 1 --users-per-org 5

# Comprehensive data for integration tests
uv run manage.py seed_data --organizations 3 --entries-per-workspace 50
```

### Demo/Staging
```bash
# Rich dataset for demonstrations
uv run manage.py seed_data --organizations 5 --users-per-org 20 --entries-per-workspace 100
```

## 📅 Date Handling

### **All Dates Are in the Past**
The seed data generates realistic historical dates for better testing and development:

- **Workspace Start Dates**: 6-12 months ago
- **Workspace End Dates**: 1-7 days from today (near-future for current testing)
- **Entry Dates**: Within workspace date ranges
- **Exchange Rate Dates**: 1-6 months ago for organizations, within workspace periods for workspaces

### **Why This Date Strategy?**
- ✅ **Realistic data**: Simulates actual historical projects that started in the past
- ✅ **Current testing**: Workspace end dates are near-future for testing current/ongoing projects
- ✅ **Better testing**: Allows testing of date-based queries, reports, and current project status
- ✅ **Balanced approach**: Historical start dates with current end dates for comprehensive testing

## ⚠️ Important Notes

### Production Environment
- **NEVER** use `--clear-existing` in production
- The command is designed for development/testing only
- Always backup your database before running in staging

### Data Relationships
- Organizations → Workspaces → Teams → Entries
- Users are assigned to organizations, then to specific roles
- Exchange rates are created for both organizations and workspaces
- All foreign key relationships are properly maintained

### Performance Considerations
- Large datasets may take several minutes to create
- Consider running during off-peak hours
- Monitor database performance during execution

## 🚨 Troubleshooting

### Common Issues

#### Date Validation Errors
- **Problem**: "Date cannot be in the future" errors
- **Solution**: Most seed data dates are in the past, but workspace end dates are intentionally 1-7 days from today for current testing
- **Note**: This prevents most future date validation conflicts while keeping workspaces current

#### Role Conflicts
- **Problem**: Users assigned multiple conflicting roles
- **Solution**: The command automatically resolves role conflicts and reports any issues
- **Check**: Look for role conflict warnings in the command output

## 🔧 Troubleshooting

### Common Issues

#### Permission Errors
```bash
# Ensure you have database write access
# Check Django user permissions
```

#### Signal Errors
- The command automatically handles signal disconnection
- If you encounter signal errors, the command will show detailed error messages

#### Duplicate Names
- Names are automatically made unique
- If conflicts occur, numbers are appended (e.g., "Foundation 1", "Foundation 2")

### Error Recovery
- If the command fails, check the error messages
- The database will be in a consistent state
- You can safely re-run the command

## 📖 Examples

### Complete Development Setup
```bash
# Clear everything and start fresh
uv run manage.py seed_data --clear-existing \
  --organizations 3 \
  --workspaces-per-org 2 \
  --teams-per-org 3 \
  --users-per-org 10 \
  --entries-per-workspace 20
```

### Add More Test Data
```bash
# Keep existing data, add more organizations
uv run manage.py seed_data --organizations 2
```

### Minimal Test Data
```bash
# Small dataset for quick testing
uv run manage.py seed_data \
  --organizations 1 \
  --workspaces-per-org 1 \
  --teams-per-org 2 \
  --users-per-org 5 \
  --entries-per-workspace 5
```

## 🤝 Contributing

When adding new management commands to this directory:

1. Follow the existing naming conventions
2. Include comprehensive help text
3. Add proper error handling with try-catch blocks
4. Document all command options
5. Update this README.md with new command information

## 📞 Support

For issues or questions about these management commands:

1. Check the command help: `uv run manage.py seed_data --help`
2. Review the command source code
3. Check Django logs for detailed error information
4. Consult the main project documentation

---

**Remember**: These commands are powerful tools for development and testing. Always use them responsibly and never in production without proper backups! 🚀
