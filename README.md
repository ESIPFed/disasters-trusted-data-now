# Trusted Data Now – ESIP Disasters Cluster

A community-curated collection of trusted tools and datasets for disaster readiness and response operations.

## About

This project maintains a comprehensive database of reliable data sources, APIs, and tools that are essential for disaster preparedness and emergency response. The collection is curated by the ESIP Disasters Cluster community and focuses on resources that are publicly accessible, actively maintained, and operationally useful.

## Features

- **Interactive Web Interface**: Browse and search through disaster-related data sources
- **Real-time Accessibility Monitoring**: Automated checking of resource availability
- **Community Contributions**: Submit new resources via Google Forms
- **Categorized Resources**: Organized by disaster type (flood, earthquake, wildfire, etc.)
- **Status Tracking**: Monitor which resources are active and publicly accessible

## Usage

### Web Interface

The main interface is available at [https://esipfed.github.io/disasters-trusted-data-now/](https://esipfed.github.io/disasters-trusted-data-now/) or locally at `index.html`. It provides:

- Search and filter capabilities
- Card and table view options
- Real-time statistics
- Direct links to resources

### Data Management

The project includes Python scripts for data management:

- `scripts/ingest_google_forms.py`: Import new submissions from Google Forms
- `scripts/check_accessibility.py`: Verify resource accessibility

### Adding Resources

New resources can be added through the Google Form linked in the web interface, or by directly editing `data.json`.

#### How to Submit a New Resource

1. Visit the [web interface](https://esipfed.github.io/disasters-trusted-data-now/)
2. Click the **"+ Submit via Google Form"** button
3. Fill out all required fields
4. Submit the form
5. Your submission will be reviewed and added during the next sync

#### How to Update an Existing Resource

Anyone can suggest updates or corrections to existing resources! Two easy ways:

**Method 1: Click "Suggest Edit" on any resource** (Easiest!)
1. Browse resources on the [web interface](https://esipfed.github.io/disasters-trusted-data-now/)
2. Click the **"✏️ Suggest Edit"** link on any resource
3. The submission form opens with the URL pre-filled
4. Fill out the form with the updated information
5. Submit - your update will be processed during the next sync

**Method 2: Submit directly via the form**
1. Go to the submission form
2. Provide the **exact URL** of the resource you want to update
3. Fill in the other fields with updated information
4. Submit - your update will be processed during the next sync

**How it works:** The system uses the resource URL as a unique identifier. When the same URL appears in a new submission, it automatically updates the existing entry rather than creating a duplicate.

#### For Submitters: Editing Your Own Submission

If you submitted a resource and want to make changes:

- If you saved the "Edit your response" link from Google Forms, you can use it to modify your submission directly
- Alternatively, use the "Update Existing Resource" form
- Both methods will update the same resource in the database

## Data Structure

Resources are stored in `data.json` with the following structure:

```json
{
  "name": "Resource Name",
  "description": "Brief description of the resource",
  "url": "https://example.com",
  "organization": "Organization Name",
  "type": ["flood", "earthquake"],
  "public": true,
  "active": true,
  "subscription": false,
  "researchOrOps": "Operation",
  "notes": "Additional notes",
  "contact": "contact@example.com"
}
```

## Contributing

Contributions are welcome! Please:

1. **New Resources**: Use the main Google Form to submit new resources
2. **Updates/Corrections**: Use the "Update Existing Resource" form to modify existing entries
3. **Direct Edits**: Advanced users can submit pull requests to modify `data.json` directly
4. Ensure all URLs are publicly accessible
5. Provide accurate descriptions and categorization
6. Include contact information when possible

### Community Guidelines

- Anyone can suggest updates to existing resources, not just the original submitter
- Updates are processed automatically based on URL matching
- All submissions are reviewed before being published

## License

This project is open source. Please respect the individual licenses of the resources listed.

## Contact

**ESIP Disasters Cluster**: https://www.esipfed.org/collaboration-areas/data-help-desk-cluster-8/

**Contributor**: Jeil Oh (jeoh@utexas.edu)

For questions about this project or to report issues, please contact the ESIP Disasters Cluster.
