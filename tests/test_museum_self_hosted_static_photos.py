"""Museum image original bytes copied to our actual static app, not external hotlinks."""
import hashlib,json,re,sys,unittest
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from export_official_museum_static_photos import canonical,generate
class MuseumSelfHostedPhotoTests(unittest.TestCase):
    def test_all_source_original_urls_in_our_public_site_and_unique_bytes(self):
        data=json.loads((ROOT/'apps/web/src/data/official-museum-photo-assets.json').read_text())
        self.assertEqual(data['source'],'https://muzei-xleb.ru')
        self.assertEqual(data['mode'],'self-hosted-static-images')
        self.assertEqual(data['count'],233)
        self.assertEqual(data['unique_static_assets'],229)
        self.assertEqual(len(data['photos']),233)
        used={}
        for original,item in data['photos'].items():
            with self.subTest(url=original):
                self.assertEqual(original,canonical(item['source_image_url']))
                self.assertEqual(item['original_sha256'],hashlib.sha256((ROOT/'.local_archive/museum-official-photos'/
                    (item['original_sha256']+'.jpg')).read_bytes()).hexdigest())
                rel=item['path'].removeprefix('/')
                self.assertRegex(rel,r'^media/museum-source/[a-f0-9]{64}\.webp$')
                binary=(ROOT/'apps/web/public'/rel)
                self.assertTrue(binary.is_file())
                self.assertEqual(binary.stat().st_size,item['bytes'])
                self.assertEqual(hashlib.sha256(binary.read_bytes()).hexdigest(),item['static_sha256'])
                with Image.open(binary) as frame:
                    self.assertEqual(frame.format,'WEBP')
                    self.assertEqual((frame.width,frame.height),(item['width'],item['height']))
                used[item['path']]=True
        self.assertEqual(len(used),229)
    def test_export_manifest_replay_works_offline(self):
        result=generate(verify_only=True)
        self.assertEqual(result['count'],233)
        self.assertEqual(result['unique'],229)
    def test_accessibility_photo_images_have_real_selfhosted_mappings(self):
        data=json.loads((ROOT/'apps/web/src/data/official-museum-photo-assets.json').read_text())
        matches=[x for x in data['photos'].values() if x['source_slug']=='accessible-museum']
        self.assertEqual(len(matches),7)
        self.assertEqual(len({x['path'] for x in matches}),7)
        for image in matches:
            self.assertEqual(image['source_page_url'],'https://muzei-xleb.ru/informaciya-dlya-mgn')
            self.assertTrue((ROOT/'apps/web/public'/image['path'].removeprefix('/')).is_file())

    def test_images_render_through_local_public_manifest_only(self):
        s=(ROOT/'apps/web/src/components/OfficialMuseumSourcePhotos.tsx').read_text()
        self.assertIn('localMuseumPhoto(item.url)',s)
        self.assertIn('photoIndex.photos',(ROOT/'apps/web/src/data/museum-photo-assets.ts').read_text())
        self.assertIn('src={src}',s)
        self.assertIn('href={src}',s)
        self.assertNotIn('src={item.url}',s)
        self.assertNotIn('href={item.url}',s)
if __name__=='__main__':unittest.main()
