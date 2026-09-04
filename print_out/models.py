from django.db import models
import socket
import os


class Printer(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Exact Windows printer name, e.g. POS-90",
    )

    display_name = models.CharField(
        max_length=150,
        blank=True,
        help_text="Friendly name shown in Clarity Retail",
    )

    server_ip = models.CharField(
        max_length=255,
        help_text=(
            "IP address or hostname of the Windows computer "
            "running the print server"
        ),
        default="127.0.0.1",
    )

    server_port = models.PositiveIntegerField(
        default=9101,
        help_text="Windows print server port",
    )

    enabled = models.BooleanField(
        default=True
    )

    is_default = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-is_default", "name"]

    def __str__(self):
        return self.display_name or self.name

    def save(self, *args, **kwargs):
        """
        Only one printer can be the default printer.
        """

        if self.is_default:
            Printer.objects.exclude(
                pk=self.pk
            ).update(
                is_default=False
            )

        super().save(*args, **kwargs)

    def get_resolved_ip(self):
        """
        Resolve the configured print-server address.

        Supported values:
            127.0.0.1
            192.168.1.50
            printer-server.local
            host.docker.internal

        host.docker.internal is useful when Django is
        running inside Docker and the Windows print server
        is running on the Docker host.
        """

        host = str(self.server_ip).strip()

        if not host:
            return host

        # Already an IP address.
        try:
            socket.inet_aton(host)
            return host
        except socket.error:
            pass

        # host.docker.internal
        if host.lower() == "host.docker.internal":

            # Inside Docker:
            # Docker Desktop normally provides this hostname.
            if os.path.exists("/.dockerenv"):

                try:
                    return socket.gethostbyname(
                        "host.docker.internal"
                    )

                except socket.gaierror:

                    # Docker/Linux fallback.
                    for fallback in (
                        "172.17.0.1",
                        "172.18.0.1",
                    ):
                        try:
                            socket.inet_aton(
                                fallback
                            )
                            return fallback
                        except socket.error:
                            continue

                # Let the connection layer report the
                # hostname if resolution failed.
                return host

            # Outside Docker, host.docker.internal is
            # generally not required.
            #
            # If your print server is on the same Windows
            # machine, use 127.0.0.1 instead.
            return host

        # Normal hostname.
        try:
            return socket.gethostbyname(host)

        except socket.gaierror:
            return host