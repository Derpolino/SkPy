import requests

from .conn import SkypeConnection
from .user import SkypeContact, SkypeContacts
from .chat import SkypeChats
from .event import SkypeEvent
from .util import SkypeObj, cacheResult


class Skype(SkypeObj):
    """
    The main Skype instance.  Provides methods for retrieving various other object types.

    Attributes:
        user (:class:`.SkypeContact`):
            Contact information for the connected account.
        contacts (:class:`.SkypeContacts`):
            Container of contacts for the connected user.
        chats (:class:`.SkypeChats`):
            Container of conversations for the connected user.
    """

    attrs = ("userId",)

    def __init__(self, user=None, pwd=None, tokenFile=None):
        """
        Create a new Skype object and corresponding connection.

        All arguments are passed to the :class:`.SkypeConnection` instance.

        Args:
            user (str): username of the connecting account
            pwd (str): password of the connecting account
            tokenFile (str): path to a file, used to cache session tokens
        """
        super(Skype, self).__init__(self)
        self.conn = SkypeConnection(user, pwd, tokenFile)
        self.userId = self.conn.user
        self.contacts = SkypeContacts(self)
        self.chats = SkypeChats(self)

    @property
    @cacheResult
    def user(self):
        json = self.conn("GET", "{0}/users/self/profile".format(SkypeConnection.API_USER),
                         auth=SkypeConnection.Auth.SkypeToken).json()
        return SkypeContact.fromRaw(self, json)

    @SkypeConnection.handle(404, regToken=True)
    def getEvents(self):
        """
        Retrieve a list of events since the last poll.  Multiple calls may be needed to retrieve all events.

        If no events occur, the API will block for up to 30 seconds, after which an empty list is returned.  As soon as
        an event is received in this time, it is returned immediately.

        Returns:
            :class:`.SkypeEvent` list: a list of events, possibly empty
        """
        events = []
        for json in self.conn.endpoints["self"].getEvents():
            events.append(SkypeEvent.fromRaw(self, json))
        return events

    def setPresence(self, online=True):
        """
        Set the user's presence (either *Online* or *Hidden*.

        Args:
            online (bool): whether to appear online or not
        """
        self.conn("PUT", "{0}/users/ME/presenceDocs/messagingService".format(self.conn.msgsHost),
                  auth=SkypeConnection.Auth.RegToken, json={"status": "Online" if online else "Hidden"})

    def setAvatar(self, image):
        """
        Update the profile picture for the current user.

        Args:
            image (file): a file-like object to read the image from
        """
        self.conn("PUT", "{0}/users/{1}/profile/avatar".format(SkypeConnection.API_USER, self.userId),
                  auth=SkypeConnection.Auth.SkypeToken, data=image.read())


class SkypeEventLoop(Skype):
    """
    A skeleton class for producing event processing programs.

    Attributes:
        autoAck (bool):
            Whether to automatically acknowledge all incoming events.
    """

    def __init__(self, user=None, pwd=None, tokenFile=None, autoAck=True):
        """
        Create a new event loop and the underlying connection.

        The ``user``, ``pwd`` and ``tokenFile``  arguments are passed to the :class:`.SkypeConnection` instance.

        Args:
            user (str): the connecting user's username
            pwd (str): the connecting user's account password
            tokenFile (str): path to a file, used to cache session tokens
            autoAck (bool): whether to automatically acknowledge all incoming events
        """
        super(SkypeEventLoop, self).__init__(user, pwd, tokenFile)
        self.autoAck = autoAck

    def loop(self):
        """
        Handle any incoming events, by calling out to :meth:`onEvent` for each one.  This method does not return.
        """
        while True:
            try:
                events = self.getEvents()
            except requests.ConnectionError:
                continue
            for event in events:
                self.onEvent(event)
                if self.autoAck:
                    event.ack()

    def onEvent(self, event):
        """
        Subclasses should implement this method to react to messages and status changes.

        Args:
            event (SkypeEvent): an incoming event
        """
        pass
