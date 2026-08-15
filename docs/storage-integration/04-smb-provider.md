# SMB provider

`SMBBinaryStore` encapsulates the pinned `smbprotocol`/`smbclient` client.
Configuration includes server, share, approved root, explicit auth mode,
timeouts, signing and encryption requirements. Authentication is not
silently downgraded; production configuration must select `smb`, and the
mock provider is rejected there.

The provider uses application-managed SMB sessions and no OS mount. A future
Kerberos/DFS mode remains an Owner inventory and certification decision.
