YourTunes is a Python web application which allows multiple users to contribute to a playlist using their individual local song files, as well as youtube videos. Using the Tornado framework to set up a server, multiple clients can connect to a virtual jukebox and choose what songs should be added to a playlist.

Install Tornado and requests using pip (pip install requests, pip install tornado)

Run termy.py from the terminal. This sets up the server. In a web browser, the host should navegate to localhost:9000. Clients should navegate to 'local_host's_IP_address:9000'. 