import structx
import unittest
import structio


class MyTestCase(unittest.TestCase):
    def test_append_remove_struct_module(self):
        self.assertFalse(hasattr(struct, 'pack_stream'))
        structio.append_to_struct_module()
        self.assertTrue(hasattr(struct, 'pack_stream'))
        structio.remove_from_struct_module()
        self.assertFalse(hasattr(struct, 'pack_stream'))

    def test_replace_reset_struct_class(self):
        self.assertFalse(hasattr(struct, 'pack_stream'))
        structio.append_to_struct_module()
        self.assertTrue(hasattr(struct, 'pack_stream'))
        structio.remove_from_struct_module()
        self.assertFalse(hasattr(struct, 'pack_stream'))


if __name__ == '__main__':
    unittest.main()
