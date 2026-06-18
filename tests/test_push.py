import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from PIL import Image

from push import push_image, save_images


class PushTests(unittest.TestCase):
    def test_save_images_writes_page_files(self):
        images = {
            2: Image.new("1", (400, 300), 255),
            1: Image.new("1", (400, 300), 255),
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            paths = save_images(images, Path(temp_dir))

            self.assertEqual(
                [path.name for path in paths],
                ["page_1.png", "page_2.png"],
            )
            self.assertTrue(all(path.exists() for path in paths))

    @patch("push.requests.post")
    def test_push_image_uses_zectrix_image_endpoint(self, post):
        post.return_value = Mock(ok=True, status_code=200)
        image = Image.new("1", (400, 300), 255)

        push_image(image, 3, "test-key", "AA:BB:CC")

        args, kwargs = post.call_args
        self.assertEqual(
            args[0],
            "https://cloud.zectrix.com/open/v1/devices/"
            "AA:BB:CC/display/image",
        )
        self.assertEqual(kwargs["headers"], {"X-API-Key": "test-key"})
        self.assertEqual(kwargs["data"], {"dither": "false", "pageId": "3"})
        self.assertEqual(kwargs["files"]["images"][0], "page_3.png")


if __name__ == "__main__":
    unittest.main()
