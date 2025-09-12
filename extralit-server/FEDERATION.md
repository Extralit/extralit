# Extralit Hub Federation Setup

This document explains how to configure your Extralit instance to authenticate with the Extralit Hub using federated identity.

## Overview

The federated identity system allows users to sign into any Extralit instance using their Extralit Hub account. This provides:

- **Single Sign-On**: Users authenticate once on the Hub, access all instances
- **Centralized User Management**: User profiles and permissions managed by the Hub
- **Enterprise Security**: Secure OIDC-based authentication flow
- **Automatic Setup**: Instances auto-register with the Hub (especially on HuggingFace Spaces)

## Quick Start

### For HuggingFace Spaces (Automatic)

If your instance is running on HuggingFace Spaces, federation setup is automatic:

1. Your Space will auto-register with the Extralit Hub on startup
2. The Hub OIDC provider will be automatically configured
3. Users can sign in using "Sign in with Extralit Hub"

Check registration status:
```bash
pdm run cli hub-auth status
```

### For Self-Hosted Instances

1. **Register with Hub**:
   ```bash
   pdm run cli hub-auth register --hub-url https://hub.extralit.ai
   ```

2. **Set Environment Variables** (optional, for persistence):
   ```bash
   export EXTRALIT_HUB_URL=https://hub.extralit.ai
   export EXTRALIT_HUB_CLIENT_ID=your_client_id
   export EXTRALIT_HUB_CLIENT_SECRET=your_client_secret
   ```

3. **Test Configuration**:
   ```bash
   pdm run cli hub-auth test-oidc
   ```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `EXTRALIT_HUB_URL` | Hub base URL | `https://hub.extralit.ai` (production)<br>`http://localhost:3000` (development) |
| `EXTRALIT_HUB_CLIENT_ID` | OAuth2 client ID | Auto-generated during registration |
| `EXTRALIT_HUB_CLIENT_SECRET` | OAuth2 client secret | Auto-generated during registration |

### HuggingFace Spaces Detection

The system automatically detects HuggingFace Spaces environment using these variables:
- `SPACE_ID` - HuggingFace Space identifier
- `SPACE_AUTHOR_NAME` - Space owner username
- `SPACE_REPO_NAME` - Space repository name

## Authentication Flow

1. **User Access**: User visits your instance
2. **Login Options**: Instance shows "Sign in with Extralit Hub" option
3. **Hub Redirect**: User is redirected to Hub for authentication
4. **User Login**: User signs in with their Hub account (Google/GitHub/email)
5. **Authorization**: Hub asks for permission to share profile with your instance
6. **Token Exchange**: Hub returns authorization code to your instance
7. **User Creation**: Instance creates local user account with Hub profile data
8. **Access Granted**: User can now use your instance with Hub identity

## OAuth2 Provider Configuration

Add the Hub provider to your OAuth2 configuration:

```python
# In your settings or configuration
OAUTH2_PROVIDERS = {
    "extralit_hub": {
        "enabled": True,
        "auto_register": True,  # Automatically create users
        "sync_user_data": True,  # Keep user data in sync
    }
}
```

## User Data Synchronization

When users authenticate via Hub, the following data is synchronized:

- **Basic Profile**: Name, email, username
- **Hub Capabilities**: GitHub Copilot access, LLM tier
- **Permissions**: Instance-specific permissions
- **Usage Quotas**: Token limits and usage tracking

## CLI Commands

### Registration Commands
```bash
# Check current status
pdm run cli hub-auth status

# Register with Hub (auto-detect environment)
pdm run cli hub-auth register

# Register with custom Hub URL
pdm run cli hub-auth register --hub-url https://your-hub.example.com

# Force re-registration
pdm run cli hub-auth register --force
```

### Testing Commands
```bash
# Test OIDC configuration
pdm run cli hub-auth test-oidc

# Clear stored credentials
pdm run cli hub-auth clear-credentials
```

## Troubleshooting

### Common Issues

1. **"Hub client credentials not available"**
   - Run `pdm run cli hub-auth register` to register your instance
   - Check that `EXTRALIT_HUB_URL` is correctly set

2. **"Registration failed: Connection refused"**
   - Verify Hub URL is accessible
   - Check firewall settings (instances need outbound HTTPS access)

3. **"Invalid redirect URI"**
   - For HF Spaces: Ensure your Space ID matches the URL
   - For self-hosted: Verify your base URL configuration

4. **"User creation failed"**
   - Check database connectivity
   - Verify user creation permissions

### Debug Logging

Enable debug logging to troubleshoot issues:

```python
import logging
logging.getLogger("extralit_server.security.authentication.oauth2.extralit_hub").setLevel(logging.DEBUG)
```

### Manual Registration

If automatic registration fails, you can register manually via the Hub UI:

1. Visit Hub admin panel
2. Go to "OAuth2 Clients" section
3. Click "Register New Client"
4. Fill in your instance details
5. Copy client ID and secret to your instance configuration

## Security Considerations

- **Client Secrets**: Store securely, never commit to version control
- **HTTPS Required**: Production instances must use HTTPS
- **Token Validation**: All Hub tokens are validated cryptographically
- **User Data**: Only necessary profile data is shared with instances
- **Audit Logging**: All authentication events are logged for security monitoring

## Development vs Production

### Development
- Hub URL defaults to `http://localhost:3000`
- Self-hosted instances are auto-approved
- Less strict validation for testing

### Production
- Hub URL defaults to `https://hub.extralit.ai`
- Custom domain instances require manual approval
- Strict security validation and audit logging

## Support

For issues with federation setup:
1. Check the troubleshooting section above
2. Review logs for specific error messages
3. Use CLI commands to diagnose configuration
4. Contact Extralit support with your client ID and error details

## Advanced Configuration

### Custom Claims Processing

You can extend user data processing by overriding the `get_user_details` method:

```python
class CustomExtralitHubOpenId(ExtralitHubOpenId):
    def get_user_details(self, response):
        user = super().get_user_details(response)
        # Add custom processing
        user['custom_field'] = response.get('custom_claim')
        return user
```

### Instance-Specific Permissions

Configure permissions based on Hub user claims:

```python
# In your user creation logic
if user_data.get('llm_access_tier') == 'premium':
    user.role = UserRole.admin
elif user_data.get('github_copilot_enabled'):
    user.role = UserRole.annotator
```