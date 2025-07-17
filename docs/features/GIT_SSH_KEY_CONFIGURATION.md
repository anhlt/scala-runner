# Git SSH Key Configuration

This feature allows you to configure SSH private keys for Git authentication, enabling push/pull operations to private repositories on GitHub, GitLab, and Bitbucket.

## API Endpoints

### Configure SSH Key
`POST /git/configure-ssh-key`

Configure an SSH private key for a workspace to enable Git authentication.

**Request Body:**
```json
{
  "workspace_name": "my-workspace",
  "private_key": "-----BEGIN OPENSSH PRIVATE KEY-----\n...\n-----END OPENSSH PRIVATE KEY-----",
  "public_key": "ssh-rsa AAAAB3NzaC1yc2E... user@host (optional)",
  "passphrase": "optional_passphrase",
  "key_name": "id_rsa"
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "workspace_name": "my-workspace",
    "key_name": "id_rsa",
    "private_key_configured": true,
    "public_key_configured": true,
    "passphrase_configured": false,
    "ssh_config_created": true,
    "message": "SSH key 'id_rsa' configured successfully for workspace 'my-workspace'"
  }
}
```

### Remove SSH Key
`DELETE /git/ssh-key/{workspace_name}`

Remove SSH key configuration for a workspace.

**Response:**
```json
{
  "status": "success",
  "data": {
    "workspace_name": "my-workspace",
    "ssh_keys_removed": true,
    "message": "SSH key configuration removed for workspace 'my-workspace'"
  }
}
```

## Usage Example

1. **Configure SSH Key:** First, configure your SSH private key for the workspace:
   ```bash
   curl -X POST "http://localhost:8000/git/configure-ssh-key" \
     -H "Content-Type: application/json" \
     -d '{
       "workspace_name": "my-project",
       "private_key": "-----BEGIN OPENSSH PRIVATE KEY-----\nYOUR_PRIVATE_KEY_HERE\n-----END OPENSSH PRIVATE KEY-----",
       "public_key": "ssh-rsa AAAAB3NzaC1yc2EAAAA... user@host"
     }'
   ```

2. **Clone Private Repository:** Now you can clone private repositories using SSH URLs:
   ```bash
   curl -X POST "http://localhost:8000/workspace/clone" \
     -H "Content-Type: application/json" \
     -d '{
       "workspace_name": "my-project",
       "git_url": "git@github.com:username/private-repo.git"
     }'
   ```

3. **Push/Pull Operations:** All subsequent Git operations will automatically use the configured SSH key:
   ```bash
   # Push changes
   curl -X POST "http://localhost:8000/git/push" \
     -H "Content-Type: application/json" \
     -d '{
       "workspace_name": "my-project",
       "remote_name": "origin",
       "branch_name": "main"
     }'
   ```

## Security Features

- **Secure Storage:** SSH keys are stored with restrictive file permissions (600 for private keys, 700 for directories)
- **Workspace Isolation:** Each workspace has its own SSH key directory and configuration
- **Environment Isolation:** SSH environment variables are temporarily set only during Git operations
- **Multiple Host Support:** SSH configuration includes GitHub, GitLab, and Bitbucket by default

## File Structure

When you configure SSH keys, the following directory structure is created:

```
{base_dir}/ssh_keys/{workspace_name}/
├── id_rsa              # Private key (permissions: 600)
├── id_rsa.pub          # Public key (permissions: 644) - optional
├── id_rsa.passphrase   # Passphrase (permissions: 600) - if provided
└── config              # SSH config (permissions: 600)
```

## Supported Git Operations

The following Git operations automatically use configured SSH keys:
- Clone repositories (`POST /workspace/clone` with SSH URLs)
- Push changes (`POST /git/push`)
- Pull changes (`POST /git/pull`)

## Notes

- SSH keys are automatically detected for SSH URLs (those starting with `git@` or `ssh://`)
- The SSH configuration includes `StrictHostKeyChecking no` for convenience in automated environments
- Multiple SSH keys per workspace are supported by using different `key_name` values
- The system creates SSH configs for common Git hosts (GitHub, GitLab, Bitbucket) 