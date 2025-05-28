import unittest
from autonomous_research_agent.main import main

class TestMain(unittest.TestCase):
    def test_main_runs_without_errors(self):
        # This test ensures that the main function runs without raising any exceptions
        try:
            main()
        except Exception as e:
            self.fail(f"main() raised {type(e).__name__} unexpectedly!")

if __name__ == '__main__':
    unittest.main() 