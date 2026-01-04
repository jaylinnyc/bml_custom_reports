"""
Odoo API Client Helper
"""
import xmlrpc.client
import ssl
import os

# Try to import config, provide helpful error if missing
try:
    from config import ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_API_KEY
except ImportError:
    print("❌ Error: config.py not found!")
    print("   Copy config.py.example to config.py and fill in your credentials.")
    exit(1)


class OdooClient:
    def __init__(self, verbose=True):
        self.url = ODOO_URL
        self.db = ODOO_DB
        self.username = ODOO_USERNAME
        self.api_key = ODOO_API_KEY
        self.uid = None
        self.models = None
        self.verbose = verbose
        self.connect()
    
    def connect(self):
        """Authenticate and connect to Odoo"""
        # Create SSL context that doesn't verify (for dev environments)
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        try:
            common = xmlrpc.client.ServerProxy(
                f'{self.url}/xmlrpc/2/common',
                allow_none=True,
                context=context
            )
            self.uid = common.authenticate(self.db, self.username, self.api_key, {})
            
            if not self.uid:
                raise Exception("Authentication failed. Check your credentials in config.py")
            
            self.models = xmlrpc.client.ServerProxy(
                f'{self.url}/xmlrpc/2/object',
                allow_none=True,
                context=context
            )
            
            if self.verbose:
                print(f"✅ Connected to Odoo (User ID: {self.uid})")
                
                # Get server version
                version_info = common.version()
                print(f"📌 Server: {version_info.get('server_version', 'Unknown')}")
            
            return True
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            print(f"   URL: {self.url}")
            print(f"   Database: {self.db}")
            print(f"   Username: {self.username}")
            raise
        return True
    
    def execute(self, model, method, *args, **kwargs):
        """Execute a method on a model"""
        return self.models.execute_kw(
            self.db, self.uid, self.api_key,
            model, method, args, kwargs
        )
    
    def search_read(self, model, domain=None, fields=None, limit=None, order=None):
        """Search and read records"""
        domain = domain or []
        kwargs = {}
        if fields:
            kwargs['fields'] = fields
        if limit:
            kwargs['limit'] = limit
        if order:
            kwargs['order'] = order
        return self.execute(model, 'search_read', domain, **kwargs)
    
    def search_count(self, model, domain=None):
        """Count records matching domain"""
        domain = domain or []
        return self.execute(model, 'search_count', domain)
    
    def get_fields(self, model, attributes=None):
        """Get fields definition for a model"""
        attributes = attributes or ['string', 'type', 'required', 'readonly', 'help']
        return self.execute(model, 'fields_get', [], {'attributes': attributes})
    
    def read(self, model, ids, fields=None):
        """Read specific records by ID"""
        kwargs = {'fields': fields} if fields else {}
        return self.execute(model, 'read', ids, **kwargs)


if __name__ == '__main__':
    # Test connection
    client = OdooClient()
    print("\n✅ Connection test successful!")
