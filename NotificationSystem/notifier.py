import subprocess
import winreg


APP_ID = "MyApp.Notifier"
APP_NAME = "Notifier"

#creates an app ID in the Windows registry to have the notification come from
def register_app_id():
    key_path = f"SOFTWARE\\Classes\\AppUserModelId\\{APP_ID}"
    try:
        key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, APP_NAME)
        winreg.CloseKey(key)
    except Exception as e:
        print(f"Registry error: {e}")

#creates a windows notification with the given title and message
def show_notification(title, message, silent=True):
    register_app_id()
    
    audio_xml = '<audio silent="true"/>' if silent else ''
    
    script = f"""
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
    [Windows.UI.Notifications.ToastNotification, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
    [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

    $template = @"
    <toast>
        <visual>
            <binding template="ToastGeneric">
                <text>{title}</text>
                <text>{message}</text>
            </binding>
        </visual>
        {audio_xml}
    </toast>
"@

    $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
    $xml.LoadXml($template)
    $toast = New-Object Windows.UI.Notifications.ToastNotification $xml
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("{APP_ID}").Show($toast)
    Start-Sleep -Seconds 3
    """
    
    subprocess.run(
        ['powershell', '-NonInteractive', '-WindowStyle', 'Hidden', '-Command', script],
        capture_output=True
    )