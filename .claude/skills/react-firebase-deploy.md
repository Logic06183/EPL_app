# React + Firebase Deployment Skill

## Description
Deploy a Next.js/React application to Firebase Hosting with automatic builds and optimizations.

## Use Cases
- Deploy frontend applications to Firebase Hosting
- Set up production builds for Next.js apps
- Configure Firebase hosting with custom domains
- Enable static site generation and export

## Prerequisites
- Firebase CLI installed (`npm install -g firebase-tools`)
- Firebase project created
- Next.js app configured with `output: 'export'`
- `.firebaserc` file with project configuration

## Steps

### 1. Configure Next.js for Static Export

Ensure `next.config.js` has:
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  output: 'export',        // Enable static export
  trailingSlash: true,     // Add trailing slashes
  distDir: 'out',          // Output directory
  images: {
    unoptimized: true      // Required for static export
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'YOUR_API_URL'
  }
}

module.exports = nextConfig
```

### 2. Configure Firebase Hosting

Create/update `firebase.json`:
```json
{
  "hosting": {
    "public": "out",
    "ignore": [
      "firebase.json",
      "**/.*",
      "**/node_modules/**"
    ],
    "rewrites": [
      {
        "source": "**",
        "destination": "/index.html"
      }
    ]
  }
}
```

### 3. Build and Deploy

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Build the application
npm run build

# Deploy to Firebase
firebase deploy --only hosting --project YOUR_PROJECT_ID
```

### 4. Deploy with Environment Variables

```bash
# Set API URL for production
NEXT_PUBLIC_API_URL=https://your-api.run.app npm run build

# Deploy
firebase deploy --only hosting --project YOUR_PROJECT_ID
```

## Verification

After deployment:
1. Check the Firebase console for deployment status
2. Visit your hosting URL (shown in deployment output)
3. Test all routes and API connections
4. Verify environment variables are working

## Common Issues

### Issue: 404 on page refresh
**Solution**: Ensure `rewrites` are configured in `firebase.json`

### Issue: Images not loading
**Solution**: Set `images: { unoptimized: true }` in `next.config.js`

### Issue: API calls failing
**Solution**: Verify `NEXT_PUBLIC_API_URL` is set correctly

### Issue: Build fails
**Solution**:
- Check for dynamic imports that don't work with static export
- Remove `getServerSideProps` (use `getStaticProps` instead)
- Ensure all API routes are external

## Environment Variables

Required environment variables:
- `NEXT_PUBLIC_API_URL`: Backend API endpoint

Optional:
- `NEXT_PUBLIC_GA_ID`: Google Analytics ID
- `NEXT_PUBLIC_SENTRY_DSN`: Error tracking

## Performance Optimization

1. **Enable caching** in `firebase.json`:
```json
{
  "hosting": {
    "public": "out",
    "headers": [
      {
        "source": "**/*.@(jpg|jpeg|gif|png|svg|webp)",
        "headers": [
          {
            "key": "Cache-Control",
            "value": "max-age=31536000"
          }
        ]
      },
      {
        "source": "**/*.@(js|css)",
        "headers": [
          {
            "key": "Cache-Control",
            "value": "max-age=31536000"
          }
        ]
      }
    ]
  }
}
```

2. **Minimize bundle size**:
   - Use dynamic imports for large components
   - Remove unused dependencies
   - Enable tree-shaking

3. **Optimize images**:
   - Use WebP format
   - Compress images before deployment
   - Use appropriate image sizes

## Rollback Procedure

If deployment fails or has issues:

```bash
# List previous versions
firebase hosting:releases:list --project YOUR_PROJECT_ID

# Rollback to previous version
firebase hosting:rollback --project YOUR_PROJECT_ID
```

## Quick Commands

```bash
# Build only
npm run build

# Deploy only
firebase deploy --only hosting

# Build and deploy
npm run build && firebase deploy --only hosting

# Deploy to specific site
firebase deploy --only hosting:YOUR_SITE_NAME

# Preview changes
firebase hosting:channel:deploy preview
```

## Integration with CI/CD

See the GitHub Actions workflow file for automated deployments.

## Monitoring

- Firebase Console: https://console.firebase.google.com
- Hosting metrics: Check bandwidth, requests, and errors
- Set up alerts for deployment failures

## Cost Optimization

Firebase Hosting free tier includes:
- 10 GB storage
- 360 MB/day bandwidth
- Free SSL certificates

Monitor usage to avoid unexpected charges.

## Security

1. Configure security rules
2. Use environment variables for sensitive data
3. Enable HTTPS only (automatic with Firebase)
4. Set up proper CORS headers for API calls

## Support

- Firebase Documentation: https://firebase.google.com/docs/hosting
- Next.js Static Export: https://nextjs.org/docs/pages/building-your-application/deploying/static-exports
