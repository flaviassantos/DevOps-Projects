import requests
import smtplib
import os
import paramiko
import linode_api4
import time
import schedule

EMAIL_ADDRESS = os.environ.get('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
LINODE_TOKEN = os.environ.get('LINODE_TOKEN')
SSH_KEY_PATH = os.environ.get('SSH_KEY_PATH')

WEBSITE = 'http://139-144-71-152.ip.linodeusercontent.com:8080/'
HOSTSERVER = '139.144.71.152'
CONTAINER_ID = "184450337d45"
LINODE_ID = 48903143

def restart_server_and_container():
    """
    Restarts a Linode server and an associated container running an application.

    This function performs two main tasks:
    1. Restarts the Linode server specified by the LINODE_ID using the Linode API.
    2. Waits for the server to be in the 'running' state and then restarts the application
       container by calling the 'restart_container' function.

    This function assumes that you have the necessary Linode API token (LINODE_TOKEN) and
    Linode server ID (LINODE_ID) configured as constants or variables before calling it.

    Returns:
    None
    """
    # restart linode server
    print('Rebooting the server...')
    client = linode_api4.LinodeClient(LINODE_TOKEN)
    nginx_server = client.load(linode_api4.Instance, LINODE_ID)
    nginx_server.reboot()

    # restart the application
    while True:
        nginx_server = client.load(linode_api4.Instance, LINODE_ID)
        if nginx_server.status == 'running':
            time.sleep(5)
            restart_container()
            break

def send_notification(email_msg):
    """
    Sends an email using the specified email address (EMAIL_ADDRESS) and
    password (EMAIL_PASSWORD) through the SMTP server (smtp.office365.com, port 587).
    The email contains a subject line indicating 'SITE DOWN' and the message specified
    by the 'email_msg' parameter.

    Make sure you have the following constants or variables
    defined:
    - EMAIL_ADDRESS: Your email address for sending the notification.
    - EMAIL_PASSWORD: The password or an application-specific password for email
      authentication.

    Args:
    email_msg (str): The message content to include in the notification email.

    Returns:
    None
    """
    print('Sending an email...')
    with smtplib.SMTP('smtp.office365.com', 587) as smtp:
        smtp.starttls()
        smtp.ehlo()
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        message = f"Subject: SITE DOWN\n{email_msg}"
        smtp.sendmail(EMAIL_ADDRESS, EMAIL_ADDRESS, message)

def restart_container():
    """
    Restarts the application container on a remote server using SSH and Docker.

    Establishes an SSH connection to a remote server specified by the
    variables HOSTSERVER and SSH_KEY_PATH, and then uses Docker to start the
    container specified by the CONTAINER_ID.

    Make sure you have the following constants or variables
    defined:
    - HOSTSERVER: The hostname or IP address of the remote server.
    - SSH_KEY_PATH: The file path to the SSH private key used for authentication.
    - CONTAINER_ID: The ID or name of the Docker container to be restarted.

    Returns:
    None
    """
    print('Restarting the application...')
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=HOSTSERVER, username='root', key_filename=SSH_KEY_PATH)
    stdin, stdout, stderr = ssh.exec_command(f'docker start {CONTAINER_ID}')
    print(stdout.readlines())
    ssh.close()


def monitor_application():
    """
    Monitors the status of an application by sending an HTTP GET request to a specified
    website (WEBSITE). If the application is running successfully (HTTP status code 200),
    it prints a success message. If the application is down (HTTP status code other than 200)
    or if a connection error occurs, it sends a notification email and attempts to restart
    the application container or the entire server, depending on the severity of the issue.

    Make sure you have the following constants or variables defined:
    - WEBSITE: The URL of the application to monitor.

    Returns:
    None
    """
    try:
        response = requests.get(WEBSITE)
        if response.status_code == 200:
            print('Application is running successfully!')
        else:
            print('Application Down. Fix it!')
            msg = f'Application returned {response.status_code}'
            send_notification(msg)
            restart_container()
    except Exception as ex:
        print(f'Connection error happened: {ex}')
        msg = 'Application not accessible at all'
        send_notification(msg)
        restart_server_and_container()


monitor_application()

schedule.every(5).minutes.do(monitor_application)

while True:
    schedule.run_pending()