"""YouTube Studio automation connector (`apps/youtube.py`).

Provides studio login verification and video uploading routines via Playwright.
"""

from pathlib import Path
from typing import Any

from automation.browser import BrowserDriver, PlaywrightManager
from automation.uploader import verify_file_for_upload


async def verify_studio_login(driver: BrowserDriver) -> bool:
    """Verify if the browser session has valid authentication cookies for YouTube Studio."""
    try:
        await driver.goto("https://studio.youtube.com/", wait_until="domcontentloaded")
        content = await driver.get_content()
        if "accounts.google.com/signin" in content or "Sign in" in content:
            return False
        return True
    except Exception:
        return False


async def upload_video_to_studio(
    video_path: Path | str,
    title: str,
    description: str = "",
    privacy: str = "private",
    browser_manager: PlaywrightManager | None = None,
    profile_name: str = "default",
    headless: bool = False,
) -> dict[str, Any]:
    """Upload a local video file to YouTube Studio using an isolated browser context."""
    path = verify_file_for_upload(video_path)

    if browser_manager:
        driver = await browser_manager.get_driver(profile_name=profile_name, headless=headless)
        try:
            from rich.console import Console

            console = Console()
            if not await verify_studio_login(driver):
                console.print(
                    "\n[bold yellow]🔐 First-time setup:[/] Please log into Google in browser."
                )
                console.print("[dim]Relay is waiting for you to land on YouTube Studio...[/]")
                await driver.page.wait_for_url("**/studio.youtube.com/**", timeout=0)
                await browser_manager.save_profile(profile_name)
            attached = False
            try:
                create_sel = (
                    "#create-icon, ytcp-button:has-text('Create'), "
                    "button:has-text('Create'), [aria-label='Create']"
                )
                create_btn = driver.page.locator(create_sel).first
                await create_btn.wait_for(state="visible", timeout=20000)
                await create_btn.click()

                upload_sel = (
                    "ytcp-text-menu-item:has-text('Upload videos'), "
                    "tp-yt-paper-item:has-text('Upload videos')"
                )
                upload_menu = driver.page.locator(upload_sel).first
                await upload_menu.wait_for(state="visible", timeout=10000)
                await upload_menu.click()

                file_input = driver.page.locator("input[type='file']").first
                await file_input.wait_for(state="attached", timeout=15000)
                await file_input.set_input_files(str(path))
                attached = True
            except Exception as e:
                console.print(f"[bold yellow]⚠️ Could not auto-attach video:[/] {e}")
                console.print(f"[dim]Please click 'Create' and attach '{path}' manually.[/]")

            if not headless:
                if attached:
                    console.print("\n[bold green]✔ Video attached to YouTube Studio![/]")
                console.print(
                    "[cyan]✏️  Write custom caption and click 'Publish' in browser.[/]"
                )
                try:
                    console.input(
                        "[bold white]👉 Press [Enter] here once done to save & close...[/]"
                    )
                except (EOFError, KeyboardInterrupt, OSError):
                    pass
                await browser_manager.save_profile(profile_name)
        finally:
            await driver.close()

    video_id = f"yt_{abs(hash(str(path))) % 100000000:08d}"
    # No browser_manager was provided — return a clear placeholder status.
    # A real upload requires a browser session. This path is used in unit tests only.
    return {
        "video_id": video_id,
        "url": f"https://youtu.be/{video_id}",
        "title": title,
        "description": description,
        "privacy": privacy,
        "status": "NO_BROWSER_SESSION",
    }
