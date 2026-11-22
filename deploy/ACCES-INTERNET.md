# Acces internet sans ouvrir de ports : Cloudflare Tunnel

Pour rendre le site accessible depuis internet sans toucher a la box
(recommande pour un Raspberry Pi derriere une box domestique), on utilise un
tunnel Cloudflare. Il faut un nom de domaine gere par Cloudflare (gratuit).

## Sur le Raspberry Pi

```bash
# installation (Debian/Raspberry Pi OS 64 bits)
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main" | sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt update && sudo apt install -y cloudflared

# connexion au compte Cloudflare
cloudflared tunnel login

# creation du tunnel
cloudflared tunnel create suivi-matos

# fichier de configuration ~/.cloudflared/config.yml
cat > ~/.cloudflared/config.yml <<'EOF'
tunnel: suivi-matos
credentials-file: /home/pi/.cloudflared/TOKEN-DU-TUNNEL.json
ingress:
  - hostname: suivi.mondomaine.fr
    service: http://127.0.0.1:8000
  - service: http_status:404
EOF

# enregistrement du nom de domaine (DNS CNAME automatique)
cloudflared tunnel route dns suivi-matos suivi.mondomaine.fr

# service au demarrage
sudo cloudflared service install
```

Alternative sans nom de domaine : Tailscale (reseau prive, l'application reste
joignable uniquement par les appareils du reseau) :

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

Puis le site est accessible sur http://IP-TAILSCALE-DU-PI:8000.

## Option classique : ouverture de ports sur la box

1. Reverser proxy nginx (`deploy/nginx-suivi-matos.conf`) :
   ```bash
   sudo cp deploy/nginx-suivi-matos.conf /etc/nginx/sites-available/suivi-matos
   sudo ln -s /etc/nginx/sites-available/suivi-matos /etc/nginx/sites-enabled/
   sudo nginx -t && sudo systemctl reload nginx
   ```
2. Rediriger le port 80 (ou 443) de la box vers l'IP locale du Pi.
3. Utiliser un DNS dynamique (DuckDNS, etc.) si l'IP publique n'est pas fixe.

Attention : sans authentification, le site est alors public. Ne pas ouvrir de
ports tant que l'authentification n'est pas en place, privilegier Cloudflare
Tunnel restreint ou Tailscale.
