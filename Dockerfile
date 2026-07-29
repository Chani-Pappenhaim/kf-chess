# The KungFu Chess server, packaged to run the same anywhere.
# Only the networked server runs here - the graphical client needs a display and
# stays on the host.
FROM python:3.12-slim

# NetFree CA: the local network filters HTTPS, so without its certificate the
# pip download below fails on SSL. This installs the bundle to /etc/ca-bundle.crt
# and points the SSL tools (and pip) at it. A no-op off the NetFree network.
ADD https://netfree.link/cacert/united/x2/unix.sh /home/netfree-unix-ca.sh
RUN cat /home/netfree-unix-ca.sh | sh
ENV SSL_CERT_FILE=/etc/ca-bundle.crt
ENV REQUESTS_CA_BUNDLE=/etc/ca-bundle.crt
ENV PIP_CERT=/etc/ca-bundle.crt

WORKDIR /app

# Install dependencies first, in their own layer, so code changes do not force a
# reinstall on every build.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Then the code itself.
COPY . .

# The websocket port the server listens on (see config.SERVER_PORT).
EXPOSE 8765

CMD ["python", "-m", "server"]
