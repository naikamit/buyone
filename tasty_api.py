def __init__(self, username, password, environment='sandbox'):
        """
        Initialize the Tasty Trade API client
        
        Args:
            username: Tasty Trade username or email
            password: Tasty Trade password
            environment: 'sandbox' or 'production'
        """
        # Validate credentials aren't None or empty
        if not username or username.strip() == '':
            raise ValueError("Tasty Trade username is required and cannot be empty")
        if not password or password.strip() == '':
            raise ValueError("Tasty Trade password is required and cannot be empty")
            
        self.username = username
        self.password = password
        self.environment = environment
        self.session_token = None
        self.account_number = None
        
        # Set the base URL based on the environment
        self.base_url = 'https://api.tastyworks.com' if environment == 'production' else 'https://api.cert.tastyworks.com'
        
        # Store API calls for dashboard display
        self.api_calls = []
