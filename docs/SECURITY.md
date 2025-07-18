# 🔐 WHOOP MCP Security Guidelines

## 🚨 Critical Security Requirements

### Never Commit Sensitive Data
- ❌ **API keys** (fly.io deployment keys)
- ❌ **WHOOP credentials** (client ID/secret)
- ❌ **Authentication tokens** (whoop_token.json)
- ❌ **Environment files** (.env)

### What's Protected by .gitignore
```
.env                     # Environment variables
whoop_token.json        # WHOOP OAuth tokens
whoop_custom_prompt.json # Custom prompts
__pycache__/            # Python cache
*.py[oc]                # Compiled Python
```

## 🛡️ Security Best Practices

### 1. Environment Variables
```bash
# Use .env.example as template
cp .env.example .env

# Fill in your credentials
WHOOP_CLIENT_ID=your_actual_client_id
WHOOP_CLIENT_SECRET=your_actual_client_secret
```

### 2. API Key Management
```bash
# Generate secure API keys
openssl rand -hex 32

# Store in fly.io secrets (NOT in code)
flyctl secrets set API_SECRET_KEY=your_generated_key
```

### 3. Code Examples
Replace placeholders in documentation:
- `YOUR_API_KEY_HERE` → your actual API key
- `your_whoop_client_id_here` → your WHOOP client ID
- `your_whoop_client_secret_here` → your WHOOP client secret

## 🔍 Security Checklist

Before committing code:
- [ ] No API keys in files
- [ ] No credentials in documentation  
- [ ] .env file not committed
- [ ] Token files not committed
- [ ] Only placeholder values in examples

## 🚨 If You Accidentally Committed Secrets

### Immediate Actions:
1. **Rotate compromised credentials immediately**
2. **Remove from current files** (as done above)
3. **Clean git history** if necessary:
```bash
# Remove file from all history (destructive!)
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch .env' \
  --prune-empty --tag-name-filter cat -- --all

# Force push (only if repository is private!)
git push origin --force --all
```

### For Public Repositories:
- **Assume all committed secrets are compromised**
- **Rotate ALL credentials immediately**
- **Consider repo deletion/recreation for severe cases**

## 📋 Current Status

✅ **All sensitive data removed** from markdown guides
✅ **Security warnings added** to all documentation
✅ **.env properly git-ignored**
✅ **.env.example template** created for new users
✅ **No sensitive data found** in git history

## 📞 Emergency Response

If you suspect credentials are compromised:

1. **Immediately rotate** all API keys and credentials
2. **Check fly.io logs** for unauthorized access
3. **Review WHOOP developer dashboard** for suspicious activity
4. **Update all affected systems** with new credentials

## 🎯 Going Forward

- **Always use environment variables** for secrets
- **Never hardcode credentials** in any files
- **Review code before committing** for sensitive data
- **Use .env.example** as template for new setups

Your WHOOP MCP deployment is now secure! 🛡️