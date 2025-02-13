# PR Bot - Developer Guide

## Core Components

### Authentication System
- Token generation: `/utils/token_generator.py`
- Token validation: `/utils/token_validator.py`
- Token format: `PRB-{user_id}-{timestamp}-{usage_count}-{hash}`

### Site Management (Developer Only)
Access via: `python pr.py --dev-mode {dev_token}`

1. Site Operations: 

### Security Considerations
1. Token Generation
   - Encrypted with AES-256
   - Time-based expiration
   - Usage count tracking
   - IP logging for abuse prevention

2. Developer Access
   - Separate dev tokens
   - Full site management access
   - Token management capabilities
   - Usage analytics

### Adding New Sites
1. Required Information: 

2. Form Field Mapping:
   - Map all required fields
   - Add field validation rules
   - Define success indicators
   - Set required delays

### Maintenance
1. Token Cleanup
   - Remove expired tokens
   - Track usage patterns
   - Monitor abuse

2. Site Verification
   - Check site availability
   - Verify form fields
   - Update XPaths if needed
   - Test signup process

### Analytics
- Token usage tracking
- Success rate monitoring
- Error pattern analysis
- User activity logging

# Start in developer mode
python pr.py --dev-mode YOUR_DEV_TOKEN

# Generate user token
python pr.py --generate-token USER_ID USAGE_COUNT

# View analytics
python pr.py --analytics

# Normal usage with token
python pr.py --token YOUR_TOKEN

# Check token status
python pr.py --check-token YOUR_TOKEN