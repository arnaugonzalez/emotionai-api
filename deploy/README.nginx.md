### EmotionAI Nginx + Self-signed TLS Setup

This setup places Nginx in front of FastAPI (Uvicorn) on the same EC2 instance.
- FastAPI listens on 127.0.0.1:8000
- Nginx terminates TLS with a self-signed certificate and proxies to FastAPI
- HTTP is redirected to HTTPS

#### Prerequisites
- EC2 Security Group allows inbound TCP 80 and 443.
- Uvicorn is bound to 127.0.0.1:8000 (not 0.0.0.0) in production.

#### 1) Configure `.env.deploy`
Create/edit at repo root:

```
EC2_IP=REPLACE_WITH_ELASTIC_IP           # e.g. 3.252.222.111
FLUTTER_APP_DIR=REPLACE_OR_EMPTY         # e.g. mobile_app/ (relative to repo root). Leave empty to skip Flutter steps.
NGINX_CONF_DEST=/etc/nginx/conf.d/emotionai.conf
NGINX_SSL_DIR=/etc/nginx/ssl
```

#### 2) Generate self-signed IP certificate on the EC2
Run on the EC2 so private keys never leave the server:

```
cd /path/to/repo/emotionai-api
bash scripts/gen_self_signed_ip_cert.sh
```

This creates:
- `/etc/nginx/ssl/emotionai.crt`
- `/etc/nginx/ssl/emotionai.key` (chmod 600)

#### 3) Install Nginx and deploy the config
Copy the config file to the server (e.g., via scp or SSM). Then on the EC2:

```
cd /path/to/repo/emotionai-api
bash deploy/ec2/install_nginx_and_conf.sh
```

This will:
- Install Nginx (via dnf) if missing
- Ensure `/etc/nginx/ssl` exists
- Copy `deploy/nginx/emotionai.conf` to `/etc/nginx/conf.d/emotionai.conf`
- Validate Nginx config and reload

#### 4) Flutter app certificate pinning/trust (optional)
If `FLUTTER_APP_DIR` is set and exists, the cert generation script copies the public cert to the Flutter app at `assets/certs/emotionai_server.crt` and ensures `pubspec.yaml` includes it.

Example pinning stub (Dart): see `lib/network/pinned_http_client.dart` in your Flutter app directory. It demonstrates loading the bundled PEM and overriding `badCertificateCallback` for certificate pinning.

Minimal concept (do not copy verbatim, see stub file):
```dart
final context = SecurityContext(withTrustedRoots: false);
final bytes = await rootBundle.load('assets/certs/emotionai_server.crt');
context.setTrustedCertificatesBytes(bytes.buffer.asUint8List());
final client = HttpClient(context: context);
client.badCertificateCallback = (cert, host, port) {
  // Compare cert or public key fingerprint here
  return true; // accept only if it matches
};
```

#### Notes
- Ensure Uvicorn binds `127.0.0.1:8000`.
- In production, do not expose port 8000 in the Security Group.

#### Troubleshooting
- `nginx -t` must report syntax OK before reload.
- If cert changes, rerun the cert script and reload Nginx.
