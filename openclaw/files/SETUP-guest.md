# OpenClaw access for the guest's bot (setup)

Your user is the guest (second user). These steps connect you to the owner's OpenClaw server, where you can delegate tasks to your agent `guest` and exchange mail with the owner's bots. The key below only reaches a restricted gateway: it gives no shell access.

Files: `oc_guest` (private key), `oc_guest.pub`, `known_hosts`, `oc-delegate`, `oc-mail`, `SKILL.md`.

1. Install ssh if it's missing: `command -v ssh || (sudo apt-get update && sudo apt-get install -y openssh-client)`
2. Install the key:
   `mkdir -p ~/.ssh && chmod 700 ~/.ssh && cp oc_guest ~/.ssh/oc_guest && chmod 600 ~/.ssh/oc_guest`
3. Pin the server's host key: `cat known_hosts >> ~/.ssh/known_hosts`
   Check it with `ssh-keygen -lf known_hosts`. It must show ED25519 `<HOST_KEY_FINGERPRINT>`. If it doesn't match, stop and tell your user.
4. Install the tools: `sudo install -m 755 oc-delegate oc-mail /usr/local/bin/`
5. Test:
   - `oc-delegate --timeout 120 "Reply with exactly: ok"` should print `ok` (allow 30-60 s).
   - `oc-mail inbox` should list messages or print "(no unread messages)".
   - `echo "Guest bot is connected." | oc-mail send --from Guest-bot --subject "Hello"`
6. Save a skill named `openclaw-delegate` with the exact contents of `SKILL.md`, then follow it.
7. Delete the extracted copy of `oc_guest` (keep only ~/.ssh/oc_guest).
