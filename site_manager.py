class SiteManager:
    def __init__(self):
        self.sites_file = 'sites.json'
        self.load_sites()

    def add_site(self, site_data: dict):
        """
        Add new PR site
        
        Required site_data format:
        {
            "name": "Site Name",
            "url": "https://example.com",
            "type": "primary/secondary",
            "enabled": true,
            "form_fields": {
                "field_name": {
                    "xpath": "//input[@name='field']",
                    "type": "text/select/radio",
                    "validation": "regex_pattern"
                }
            }
        }
        """
        # Site validation and addition logic 