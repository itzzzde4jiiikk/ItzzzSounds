import unittest
from pypresence import ActivityType
from itzzzsounds.discord.rpc import resolve_activity_type, DiscordRpcManager


class TestDiscordRpc(unittest.TestCase):
    def test_resolve_activity_type(self):
        self.assertEqual(resolve_activity_type("listening"), ActivityType.LISTENING)
        self.assertEqual(resolve_activity_type("слушает"), ActivityType.LISTENING)
        self.assertEqual(resolve_activity_type("LISTEN"), ActivityType.LISTENING)
        self.assertEqual(resolve_activity_type(2), ActivityType.LISTENING)
        self.assertEqual(resolve_activity_type(ActivityType.LISTENING), ActivityType.LISTENING)

        self.assertEqual(resolve_activity_type("playing"), ActivityType.PLAYING)
        self.assertEqual(resolve_activity_type("играет"), ActivityType.PLAYING)
        self.assertEqual(resolve_activity_type(0), ActivityType.PLAYING)

        self.assertEqual(resolve_activity_type("watching"), ActivityType.WATCHING)
        self.assertEqual(resolve_activity_type("competing"), ActivityType.COMPETING)

        # Fallback to LISTENING
        self.assertEqual(resolve_activity_type("unknown"), ActivityType.LISTENING)

    def test_rpc_manager_default_activity(self):
        manager = DiscordRpcManager(enabled=False)
        self.assertEqual(manager.activity_type, ActivityType.LISTENING)


if __name__ == "__main__":
    unittest.main()
