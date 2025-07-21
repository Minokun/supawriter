import asyncio
import logging
import os
from playwright.async_api import async_playwright
from utils.history_utils import save_image_to_user_dir

# Configure logging
logger = logging.getLogger(__name__)

async def take_webpage_screenshot(url, username, filename=None, full_page=True, width=1280, height=800):
    """
    Take a screenshot of a webpage using Playwright.
    
    Args:
        url (str): The URL of the webpage to screenshot
        username (str): The username to save the screenshot for
        filename (str, optional): The filename to save the screenshot as
        full_page (bool, optional): Whether to take a screenshot of the full page
        width (int, optional): The width of the viewport
        height (int, optional): The height of the viewport
        
    Returns:
        tuple: (file_path, url_path) - The file path and URL path to access the screenshot
    """
    logger.info(f"Taking screenshot of {url} for user {username}")
    
    try:
        async with async_playwright() as p:
            # Launch browser with additional options
            browser = await p.chromium.launch(args=['--disable-web-security', '--no-sandbox'])
            
            # Create a new page
            context = await browser.new_context(
                viewport={"width": width, "height": height}
            )
            page = await context.new_page()
            
            # Set default timeout for all operations - increased to handle complex pages
            page.set_default_timeout(30000)
            
            # Set specific timeout just for navigation - increased for better reliability
            page.set_default_navigation_timeout(40000)
            
            # Navigate to the URL with a more reliable wait strategy
            try:
                logger.info(f"Navigating to {url}")
                # First try with 'domcontentloaded' which is faster
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                # Then wait for network to be idle with a separate call
                logger.info("Waiting for network idle")
                await page.wait_for_load_state("networkidle", timeout=15000)
            except Exception as nav_error:
                logger.warning(f"Navigation with networkidle failed: {nav_error}. Continuing with screenshot anyway.")
            
            # Wait longer for animations, fonts, and dynamic content to load
            logger.info("Waiting for additional content to load")
            await asyncio.sleep(5)
            
            # Wait for fonts to be loaded
            logger.info("Waiting for fonts to load")
            try:
                # Execute JavaScript to check if document fonts are loaded
                await page.evaluate('''
                    () => {
                        if (document.fonts && typeof document.fonts.ready === 'object') {
                            return document.fonts.ready;
                        }
                        return true; // If document.fonts not supported, continue anyway
                    }
                ''')
                logger.info("Fonts loaded successfully")
            except Exception as font_error:
                logger.warning(f"Error waiting for fonts: {font_error}")
            
            # Take screenshot with longer timeout
            logger.info("Taking screenshot")
            screenshot_bytes = await page.screenshot(full_page=full_page, timeout=60000)
            
            # Close browser
            await browser.close()
            
            # Generate filename if not provided
            if not filename:
                # Extract a name from the URL
                import re
                from urllib.parse import urlparse
                parsed_url = urlparse(url)
                path_parts = parsed_url.path.split('/')
                name_part = next((part for part in reversed(path_parts) if part), 'screenshot')
                name_part = re.sub(r'[^\w\-_.]', '_', name_part)
                filename = f"{name_part}_screenshot.png"
            
            # Save screenshot
            file_path, url_path = save_image_to_user_dir(username, screenshot_bytes, filename)
            
            logger.info(f"Screenshot saved to {file_path}")
            return file_path, url_path
            
    except Exception as e:
        logger.error(f"Error taking screenshot: {str(e)}")
        raise e

def take_webpage_screenshot_sync(url, username, filename=None, full_page=True, width=1280, height=800):
    """
    Synchronous wrapper for take_webpage_screenshot.
    """
    try:
        # Use nest_asyncio if we're in a Jupyter/IPython environment
        try:
            import nest_asyncio
            nest_asyncio.apply()
        except ImportError:
            pass
        
        # Check if URL is accessible before attempting screenshot
        import requests
        from urllib.parse import urlparse
        
        # Parse the URL to handle localhost properly
        parsed_url = urlparse(url)
        if parsed_url.netloc == 'localhost' or parsed_url.netloc.startswith('localhost:'):
            # For localhost URLs, try to check if the server is responding
            try:
                logger.info(f"Checking if localhost URL is accessible: {url}")
                response = requests.get(url, timeout=3)
                if response.status_code >= 400:
                    logger.warning(f"URL returned status code {response.status_code}")
            except requests.exceptions.RequestException as req_err:
                logger.warning(f"Could not connect to localhost URL: {req_err}")
                # Continue anyway as Playwright might still be able to handle it
        
        # Run the async function
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(take_webpage_screenshot(url, username, filename, full_page, width, height))
    except Exception as e:
        logger.error(f"Error in synchronous screenshot function: {str(e)}")
        raise e
