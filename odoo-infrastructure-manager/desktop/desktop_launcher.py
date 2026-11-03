import os
import platform
import socket
import sys
import threading
import time
import traceback
import webbrowser
from pathlib import Path


def write_log(msg):
    try:
        log_path = APP_DIR / "launcher.log"
        with open(str(log_path), "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass


try:
    import pystray
    from PIL import Image, ImageDraw

    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False


def is_frozen():
    return getattr(sys, "frozen", False)


def get_bundle_dir():
    if is_frozen():
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def get_app_dir():
    if is_frozen():
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BUNDLE_DIR = get_bundle_dir()
APP_DIR = get_app_dir()

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE", "config.settings.desktop"
)
os.environ["APP_DIR"] = str(APP_DIR)
os.environ["BUNDLE_DIR"] = str(BUNDLE_DIR)

SERVER_HOST = "127.0.0.1"
DESIRED_PORT = 8000

SHUTDOWN_EVENT = threading.Event()
ACTUAL_PORT = DESIRED_PORT
def create_icon_image():
    size = (32, 32)
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle([0, 0, 31, 31], radius=8, fill="#0E5A45")
    tiles = (
        ([7, 7, 14, 14], "#E3A83F"),
        ([18, 7, 25, 14], "#FFFFFF"),
        ([7, 18, 14, 25], "#FFFFFF"),
        ([18, 18, 25, 25], "#E3A83F"),
    )
    for bounds, color in tiles:
        draw.rounded_rectangle(bounds, radius=2, fill=color)
    return image


def find_free_port(start_port=8000, max_attempts=20):
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((SERVER_HOST, port))
                return port
            except OSError:
                continue
    return start_port


def initialize_database():
    try:
        write_log("Initializing database...")
        import django

        django.setup()
        write_log("Django setup OK")

        from django.core.management import call_command

        call_command("migrate", "--run-syncdb", verbosity=0)
        write_log("Migrations done")

        dirs_to_ensure = [
            APP_DIR / "staticfiles",
            APP_DIR / "media",
            APP_DIR / "backup",
        ]
        for d in dirs_to_ensure:
            d.mkdir(parents=True, exist_ok=True)
            write_log(f"Ensured dir: {d}")

        try:
            call_command("collectstatic", "--noinput", verbosity=0)
            write_log("Collectstatic done")
        except Exception as e:
            write_log(f"Collectstatic error: {e}")

    except Exception as e:
        write_log(f"DB init error: {e}")

        write_log(traceback.format_exc())


def start_server(port):
    server_started = threading.Event()

    def run_waitress():
        try:
            write_log(f"Starting server on port {port}...")
            import django

            django.setup()
            write_log("Django setup OK for server")

            from waitress import serve

            from config.wsgi import application

            write_log(f"Waitress serving on {SERVER_HOST}:{port}")
            server_started.set()

            serve(
                application,
                host=SERVER_HOST,
                port=port,
                threads=4,
                url_scheme="http",
            )
        except ImportError as e:
            write_log(f"Import error: {e}, falling back to runserver")
            try:
                import django

                django.setup()
                from django.core.management import call_command

                server_started.set()
                call_command("runserver", f"{SERVER_HOST}:{port}", use_reloader=False)
            except Exception as e2:
                write_log(f"Fallback error: {e2}")
                write_log(traceback.format_exc())
                server_started.set()
        except Exception as e:
            write_log(f"Server error: {e}")
            write_log(traceback.format_exc())
            server_started.set()

    thread = threading.Thread(target=run_waitress, daemon=True)
    thread.start()
    server_started.wait(timeout=10)
    write_log(f"Server thread started for port {port}")


def open_browser(port):
    app_url = f"http://127.0.0.1:{port}/"
    write_log(f"Opening browser: {app_url}")

    time.sleep(3)

    for attempt in range(20):
        time.sleep(1)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.settimeout(1)
                s.connect(("127.0.0.1", port))
                write_log(f"Server ready on port {port}")
                break
            except (ConnectionRefusedError, OSError):
                if attempt == 19:
                    write_log(f"Server not ready after 20 attempts on port {port}")

    try:
        webbrowser.open(app_url, new=2)
        write_log(f"Browser opened: {app_url}")
    except Exception as e:
        write_log(f"Browser error: {e}")


def run_tray(icon):
    icon.run()


def on_open(icon, item):
    global ACTUAL_PORT
    try:
        webbrowser.open(f"http://127.0.0.1:{ACTUAL_PORT}/", new=2)
        write_log(f"Tray: opened browser on port {ACTUAL_PORT}")
    except Exception as e:
        write_log(f"Tray open error: {e}")


def on_exit(icon, item):
    write_log("User requested exit")
    icon.stop()
    SHUTDOWN_EVENT.set()
    os._exit(0)


def show_tray_notification(icon, text):
    try:
        icon.notify(text, title="Enterprise Template")
    except Exception:
        pass


def main():
    global ACTUAL_PORT
    write_log("=== Application starting ===")
    write_log(f"Frozen: {is_frozen()}")
    write_log(f"BUNDLE_DIR: {BUNDLE_DIR}")
    write_log(f"APP_DIR: {APP_DIR}")

    hostname = socket.gethostname()
    system = platform.system()

    os.environ.setdefault("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

    port = find_free_port(DESIRED_PORT)
    ACTUAL_PORT = port
    write_log(f"Using port: {port}")

    print("=" * 60)
    print("        Django Enterprise Template".center(58))
    print("=" * 60)
    print(f"  Hostname:           {hostname}")
    print(f"  OS:                 {system}")
    print(f"  Port:               {port}")
    print("-" * 60)
    print("  Local access:")
    print(f"    http://127.0.0.1:{port}/")
    print()
    print("=" * 60)
    print()

    db_thread = threading.Thread(target=initialize_database, daemon=True)
    db_thread.start()
    db_thread.join(timeout=30)

    start_server(port)

    browser_thread = threading.Thread(target=open_browser, args=(port,), daemon=True)
    browser_thread.start()

    if HAS_TRAY:
        image = create_icon_image()
        menu = pystray.Menu(
            pystray.MenuItem("Open Browser", on_open),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", on_exit),
        )
        icon = pystray.Icon(
            "enterprise-template",
            image,
            "Enterprise Template",
            menu,
        )
        write_log("Starting system tray icon")

        def notify_when_ready():
            time.sleep(5)
            show_tray_notification(
                icon, f"Server running\nhttp://127.0.0.1:{ACTUAL_PORT}/"
            )

        threading.Thread(target=notify_when_ready, daemon=True).start()

        run_tray(icon)
    else:
        write_log("No system tray support, using fallback")
        try:
            while not SHUTDOWN_EVENT.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
