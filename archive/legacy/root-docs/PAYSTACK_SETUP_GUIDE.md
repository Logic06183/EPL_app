# PayStack Payment Setup Guide

## 🚀 Quick Setup (5 Minutes)

Your app is ready to receive payments! Here's exactly what you need to do to start getting paid:

## 1. Create PayStack Account

1. **Sign up**: Go to https://paystack.com/signup
2. **Verify your business**: Upload business documents (if needed)
3. **Get verified**: Usually takes 24-48 hours for SA businesses

## 2. Get Your API Keys

Once verified, get your keys from the PayStack dashboard:

1. Go to **Settings** → **API Keys & Webhooks**
2. Copy these keys:
   - **Public Key**: `pk_test_...` (for frontend)
   - **Secret Key**: `sk_test_...` (for backend)
   - **Webhook Secret**: `whsec_...` (for security)

## 3. Update Your App

Replace the placeholder keys in your `.env` file:

```bash
# Edit /Users/craig/Desktop/EPL_app/.env
PAYSTACK_SECRET_KEY=sk_test_your_real_secret_key_here
PAYSTACK_PUBLIC_KEY=pk_test_your_real_public_key_here
PAYSTACK_WEBHOOK_SECRET=your_real_webhook_secret_here
```

## 4. Restart Your App

```bash
# Restart with new keys
python3 -m uvicorn api_production:app --host 0.0.0.0 --port 8001
```

## 5. Test Payments

Use PayStack test cards to verify everything works:
- **Test Card**: 4084 0840 8408 4081
- **Expiry**: Any future date
- **CVV**: Any 3 digits

## 💰 Your Pricing (Already Configured)

- **Basic**: R99.99/month ($5.50, £4.30)
- **Pro**: R199.99/month ($11.00, £8.70) 
- **Premium**: R399.99/month ($22.00, £17.40)

## 🔧 PayStack Features You Get

### Payment Methods
- ✅ **Credit/Debit Cards** (Visa, Mastercard)
- ✅ **EFT** (Electronic Fund Transfer)
- ✅ **Bank Transfer** (Direct bank deposits)
- ✅ **QR Codes** (Mobile app payments)
- ✅ **Mobile Money** (MTN, Vodacom, etc.)

### South African Optimizations
- ✅ **Local Bank Support**: All major SA banks
- ✅ **Rand (ZAR) Payments**: No currency conversion
- ✅ **Local Processing**: Faster transactions
- ✅ **Compliance**: PCI DSS certified

### International Support
- ✅ **Global Cards**: Accepts international cards
- ✅ **Multi-Currency**: Automatic conversion
- ✅ **Fraud Protection**: Advanced security

## 📊 PayStack Dashboard

Once live, you'll see:
- **Real-time transactions**
- **Revenue analytics**
- **Customer management**
- **Payout schedules**
- **Dispute handling**

## 🔄 How Subscriptions Work

1. **Customer clicks "Upgrade"** in your app
2. **PayStack payment page** opens (secure, hosted by PayStack)
3. **Customer pays** using their preferred method
4. **Webhook notifies** your app of successful payment
5. **Customer gets access** to premium features
6. **Recurring billing** happens automatically

## 💡 PayStack Fees

- **2.9% + R2** per transaction
- **No setup fees**
- **No monthly fees**
- **Payouts every 24 hours** (once verified)

## 🔒 Security Features

- **PCI DSS Level 1** compliant
- **3D Secure** authentication
- **Advanced fraud detection**
- **Encrypted data** transmission
- **GDPR compliant**

## 🚨 Important: Webhook Setup

Your app already handles webhooks at: `http://localhost:8001/api/payment/webhook`

For production, set your webhook URL in PayStack dashboard to:
`https://yourdomain.com/api/payment/webhook`

## 📱 Mobile Optimization

PayStack payment pages are:
- ✅ **Mobile responsive**
- ✅ **App-friendly**
- ✅ **Touch optimized**
- ✅ **Fast loading**

## 🎯 Go-Live Checklist

### Test Mode (Do This First)
- [ ] Get test API keys
- [ ] Update .env file
- [ ] Test with test cards
- [ ] Verify webhooks work

### Live Mode (When Ready)
- [ ] Complete business verification
- [ ] Get live API keys
- [ ] Update .env with live keys
- [ ] Set production webhook URL
- [ ] Test with real small amount
- [ ] Launch! 🚀

## 🤝 PayStack Support

- **Documentation**: https://paystack.com/docs
- **Support Email**: support@paystack.com
- **Community**: https://paystack.community
- **Status Page**: https://status.paystack.co

## 🔧 Your App's Payment Features

### Subscription Management
- ✅ **Plan selection** (Basic/Pro/Premium)
- ✅ **Secure checkout** (PayStack hosted)
- ✅ **Automatic renewal** 
- ✅ **Easy cancellation**
- ✅ **Prorated upgrades**

### User Experience
- ✅ **One-click checkout**
- ✅ **Multiple payment methods**
- ✅ **Mobile-friendly**
- ✅ **International support**
- ✅ **Instant activation**

## 🌍 International Expansion

PayStack also supports:
- 🇳🇬 **Nigeria** (primary market)
- 🇬🇭 **Ghana** (full support)
- 🇰🇪 **Kenya** (expanding)
- 🌐 **Global cards** (worldwide)

## 💰 Revenue Projections

With your pricing:
- **100 Basic users**: R9,999/month ($550)
- **50 Pro users**: R9,999/month ($550)  
- **20 Premium users**: R7,999/month ($440)
- **Total**: R27,997/month ($1,540)

After PayStack fees (~3%): **R27,157/month ($1,493)**

## 🚀 Next Steps

1. **Create PayStack account** (today)
2. **Get API keys** (24-48 hours)
3. **Update app configuration** (5 minutes)
4. **Test payments** (10 minutes)
5. **Go live** and start earning! 💰

Your FPL AI Pro app is payment-ready. Just add the keys and you're earning revenue!