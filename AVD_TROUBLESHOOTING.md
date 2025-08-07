# AVD Connection Troubleshooting Guide

## ✅ Quick Test Steps

1. **Test Backend is Running:**
   ```
   Open browser: http://localhost:8000/test/phone
   Should show: ✅ Phone connection successful!
   ```

2. **Test AVD Connection:**
   ```
   In AVD Chrome browser: http://10.0.2.2:8000/test/phone
   Should show: ✅ Phone connection successful!
   ```

3. **Test from Flutter App:**
   ```dart
   const String baseUrl = 'http://10.0.2.2:8000';
   ```

## 🚨 Common Issues & Solutions

### Issue 1: "Connection Refused" in AVD
**Cause:** Backend not binding to all interfaces
**Solution:** 
- Make sure backend runs with: `--host 0.0.0.0`
- ✅ Your backend is already configured correctly

### Issue 2: AVD Chrome browser can't reach 10.0.2.2:8000
**Solutions:**
1. **Restart AVD completely**
2. **Check AVD network settings:**
   - Cold Boot your AVD (not just restart)
   - Settings > Apps > Chrome > Storage > Clear Data

### Issue 3: Flutter app shows network error
**Solutions:**
1. **Add network permissions to Android manifest:**
   ```xml
   <!-- android/app/src/main/AndroidManifest.xml -->
   <uses-permission android:name="android.permission.INTERNET" />
   <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
   ```

2. **Allow HTTP traffic (for development):**
   ```xml
   <!-- In <application> tag -->
   <application
       android:usesCleartextTraffic="true"
       ...>
   ```

### Issue 4: Firewall blocking connection
**Windows Firewall Fix:**
1. Go to Windows Defender Firewall
2. Allow Python through firewall
3. Allow port 8000 through firewall

### Issue 5: AVD using wrong network interface
**Solutions:**
1. **Try alternative AVD URLs:**
   ```
   http://10.0.2.2:8000  (standard)
   http://10.0.3.2:8000  (some AVD configs)
   http://192.168.1.180:8000  (your actual IP)
   ```

2. **Check AVD network mode:**
   - AVD Manager > Edit AVD > Advanced Settings
   - Network Speed: Full
   - Network Latency: None

## 🔍 Debug Steps

### Step 1: Test with AVD Browser
1. Open AVD
2. Open Chrome browser in AVD
3. Go to: `http://10.0.2.2:8000/test/phone`
4. Should see success message

### Step 2: Check Flutter HTTP Client
```dart
// Test code to add in your Flutter app
void testConnection() async {
  try {
    final response = await http.get(
      Uri.parse('http://10.0.2.2:8000/health/')
    );
    print('Status: ${response.statusCode}');
    print('Body: ${response.body}');
  } catch (e) {
    print('Error: $e');
  }
}
```

### Step 3: Check AVD Network
```bash
# In AVD terminal/shell
ping 10.0.2.2
curl http://10.0.2.2:8000/health/
```

## 🚀 Working Configuration

**Backend (✅ Already configured):**
```bash
uvicorn simple_main:app --host 0.0.0.0 --port 8000 --reload
```

**Flutter API Client:**
```dart
class ApiClient {
  static const String baseUrl = 'http://10.0.2.2:8000';
  
  static Future<http.Response> get(String endpoint) async {
    return await http.get(
      Uri.parse('$baseUrl$endpoint'),
      headers: {'Content-Type': 'application/json'},
    );
  }
}
```

**Android Manifest Permissions:**
```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
<application android:usesCleartextTraffic="true">
```

## ✅ Verification Checklist

- [ ] Backend running on http://localhost:8000 ✅
- [ ] Backend accessible from http://10.0.2.2:8000 (test in AVD browser)
- [ ] Flutter app using http://10.0.2.2:8000 as base URL
- [ ] Android permissions added to manifest
- [ ] AVD has internet access
- [ ] No firewall blocking connections

## 🆘 Still Not Working?

1. **Try different AVD:**
   - Create new AVD with latest Android image
   - Use Pixel 4 API 30+ recommended

2. **Use physical device instead:**
   - Enable USB debugging
   - Use your computer's IP: `http://192.168.1.180:8000`

3. **Port forwarding (alternative):**
   ```bash
   adb reverse tcp:8000 tcp:8000
   # Then use http://localhost:8000 in Flutter app
   ``` 