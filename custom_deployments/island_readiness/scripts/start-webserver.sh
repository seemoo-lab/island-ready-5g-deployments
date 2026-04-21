#!/usr/bin/env bash
set -euo pipefail

set -a
source .env
set +a

echo "Deploying tiny web page ..."
mkdir -p /tmp/show-ip-site

cat > /tmp/show-ip-site/index.html <<EOF
<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>${THIS_IP}</title>
    <style>
      body {
        font-family: sans-serif;
        display: grid;
        place-items: center;
        height: 100vh;
        margin: 0;
        background: #f5f5f5;
      }
      div {
        padding: 2rem 3rem;
        background: white;
        border: 1px solid #ddd;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        text-align: center;
      }
      h1 { margin: 0 0 0.5rem 0; }
      p  { margin: 0; font-size: 1.2rem; }
    </style>
  </head>
  <body>
    <div>
      <h1>Hello from</h1>
      <p>${THIS_IP}</p>
    </div>
  </body>
</html>
EOF

pkill -f "python3 -m http.server 8080" || true
nohup python3 -m http.server 8080 --directory /tmp/show-ip-site > /tmp/show-ip-site/server.log 2>&1 </dev/null &

echo "  -> http://${THIS_IP}:8080"