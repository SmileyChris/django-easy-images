from easy_images.management.commands.build_img_queue import Command


def test_build_img_queue_help_mentions_deprecated():
    # Assert the help text on the command itself mentions deprecation
    text = Command.help
    assert "DEPRECATED" in text
    assert "easy_images build" in text
