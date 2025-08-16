# Firebase Deployment Guide for FPL AI Pro

## 🔥 Your Firebase App URLs

Once deployed, your app will be available at:

### **Primary URL:**
```
https://fpl-ai-pro-[random-id].web.app
```

### **Alternative URL:**
```
https://fpl-ai-pro-[random-id].firebaseapp.com
```

## 🚀 Deployment Steps

### 1. Install Firebase CLI
```bash
npm install -g firebase-tools
```

### 2. Login to Firebase
```bash
firebase login
```

### 3. Initialize Firebase Project
```bash
firebase init

# Select:
# - Hosting
# - Functions (for API)
# Choose existing project or create new one
```

### 4. Configure for Next.js + Python API

#### Frontend (Next.js):
```bash
cd frontend
npm run build
```

#### Backend (Python API):
- Firebase Functions support Python
- Your API will run as Cloud Functions

### 5. Deploy
```bash
firebase deploy
```

## 📁 Project Structure for Firebase

```
EPL_app/
├── firebase.json          ✅ Created
├── .firebaserc            (Generated)
├── functions/             (Your Python API)
│   ├── main.py           (Entry point)
│   ├── requirements.txt  (Dependencies)
│   └── api_production.py (Your existing API)
└── frontend/
    ├── .next/            (Build output)
    └── public/           (Static assets)
```

## 🔧 Firebase Configuration

### Environment Variables:
Set in Firebase Console:
```bash
firebase functions:config:set \
  app.news_api_key="e36350769b6341bb81b832a84442e6ad" \
  app.paystack_secret="your_live_key" \
  app.paystack_public="your_live_key"
```

### Custom Domain (Optional):
1. Go to Firebase Console
2. Hosting → Connect custom domain
3. Add your domain (e.g., fpl-ai-pro.com)

## 💰 Firebase Pricing

### **Spark Plan (Free):**
- 125K function invocations/month
- 1GB hosting storage
- Perfect for testing

### **Blaze Plan (Pay-as-you-go):**
- Unlimited functions
- Required for external API calls
- ~$5-25/month expected

## 🎯 Expected Firebase URLs

Based on your project, you'll likely get:
```
https://fpl-ai-pro-xyz123.web.app
https://fpl-ai-pro-xyz123.firebaseapp.com
```

## 🔥 Advantages of Firebase

✅ **Automatic HTTPS**
✅ **Global CDN**  
✅ **Auto-scaling**
✅ **Google infrastructure**
✅ **Easy CI/CD with GitHub**
✅ **Built-in analytics**

## 📱 Mobile App Support

Firebase also supports:
- Progressive Web App (PWA)
- Mobile app analytics
- Push notifications
- Real-time database updates

Would you like me to help set up the Firebase deployment?