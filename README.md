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

1. Use the Google Form to submit new resources
2. Ensure all URLs are publicly accessible
3. Provide accurate descriptions and categorization
4. Include contact information when possible

## License

This project is open source. Please respect the individual licenses of the resources listed.

## Contact

**ESIP Disasters Cluster**: https://www.esipfed.org/collaboration-areas/data-help-desk-cluster-8/
**Contributor**: Jeil Oh (jeoh@utexas.edu)

For questions about this project or to report issues, please contact the ESIP Disasters Cluster.