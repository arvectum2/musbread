<?php

declare(strict_types=1);

namespace App\Console\Commands;

use App\Models\MuseumEntry;
use App\Models\MuseumMedia;
use App\Support\MuseumAltPolicy;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Storage;
use RuntimeException;
use Throwable;

/** Provenance-verified REAL museum imagery. No substitute pictures; original
 * bytes stay in .local_archive and CMS WebP previews are private and rights
 * blocked until a human museum owner explicitly approves eventual release.
 */
final class ImportOfficialMuseumPhotos extends Command
{
    protected $signature = 'museum:import-official-photos
        {--apply : Import verified source photos into private media editor}
        {--manifest= : Path to local saved original photos manifest}';

    protected $description = 'Preserve museum original photos privately with unchanged original source and rights embargo';

    public function handle(): int
    {
        if ($this->option('apply') && app()->environment('production')) {
            $this->error('Bulk importing original photos to production is forbidden.');
            return self::FAILURE;
        }
        $path = (string)($this->option('manifest')
            ?: base_path('../../.local_archive/museum-official-photos/manifest.json'));
        try {
            $manifest = json_decode((string)file_get_contents($path),true,flags:JSON_THROW_ON_ERROR);
            if (($manifest['source']??'') !== 'https://muzei-xleb.ru'
                || ($manifest['rights_status']??'')!=='not-verified-private-only'
                || !is_array($manifest['files']??null)) {
                throw new RuntimeException('Unverified museum original-photo archive');
            }
            $snapshots=[];
            foreach (['official-workshop-pages.json','official-excursion-programs.json'] as $name) {
                $source=json_decode((string)file_get_contents(
                    base_path('../web/src/data/'.$name)),true,flags:JSON_THROW_ON_ERROR);
                if (($source['source']??'')!=='https://muzei-xleb.ru') {
                    throw new RuntimeException('Changed original source for '.$name);
                }
                foreach ($source['programs'] as $item) {
                    $slug=$item['slug']??$item['cms_slug']??null;
                    if ($slug && isset($snapshots[$slug])) {
                        throw new RuntimeException('Duplicate original CMS source slug');
                    }
                    if ($slug) $snapshots[$slug]=['item'=>$item,'snapshot'=>$name];
                }
            }
            $files=[]; $seen=[];
            foreach ($manifest['files'] as $photo) {
                $slug=$photo['cms_slug']??'';
                $snapshot=$snapshots[$slug]??null;
                $meta=$snapshot['item']??null;
                $original=$photo['original_url']??'';
                $styled=$photo['source_image_url']??'';
                $sourceHash=$photo['sha256']??'';
                $fileName=$photo['local_name']??'';
                $allowedPath='https://muzei-xleb.ru/sites/default/files/';
                $expected=preg_replace(
                    '~^https://muzei-xleb\.ru/sites/default/files/styles/[^/]+/public/~',
                    $allowedPath,$styled);
                $expected=explode('?',(string)$expected,2)[0];
                $imageIndex=$photo['source_image_index']??0;
                if (!$meta || ($photo['source_snapshot']??'')!==$snapshot['snapshot']
                    || !is_int($imageIndex) || $imageIndex<0 || $imageIndex>2
                    || !is_array($meta['image_links']??null)
                    || ($meta['image_links'][$imageIndex]['url']??'')!==$styled
                    || ($meta['source_url']??'')!==($photo['source_page_url']??'')
                    || ($meta['title']??'')!==($photo['title']??'')
                    || ($meta['html_sha256']??null)!==($photo['source_html_sha256']??null)
                    || $expected!==$original
                    || !str_starts_with($original,$allowedPath)
                    || !preg_match('/^[a-f0-9]{64}$/D',(string)$sourceHash)
                    || !preg_match('/^[a-f0-9]{64}\.(?:jpg|png|webp)$/D',(string)$fileName)
                    || !str_starts_with($fileName,$sourceHash.'.')
                    || !is_int($photo['size_bytes']??null)
                    || isset($seen[$original])) {
                    throw new RuntimeException('Original photo provenance mismatch for '.$slug);
                }
                $seen[$original]=true;
                $sourceFile=dirname($path).'/'.$fileName;
                if (!is_file($sourceFile)
                    || filesize($sourceFile)!==$photo['size_bytes']
                    || !hash_equals($sourceHash,hash_file('sha256',$sourceFile))) {
                    throw new RuntimeException('Original image file hash mismatch: '.$slug);
                }
                $entry=MuseumEntry::where('slug',$slug)->first();
                if (!$entry || $entry->status!=='draft'
                    || !in_array($entry->type,['excursion','page'],true)
                    || !str_contains($entry->slug, 'museum-')) {
                    throw new RuntimeException('Image owner must be a real private original museum program: '.$slug);
                }
                $files[]=[...$photo,'source_path'=>$sourceFile,'entry'=>$entry];
                $this->line((MuseumMedia::where('source_original_url',$original)->exists()
                    ? 'KEEP SOURCE' : 'NEW PRIVATE ORIGINAL').' '.$slug
                    .' ← '.$original);
            }
            if (!$this->option('apply')) {
                $this->info('Dry run: original bytes and CMS untouched.');
                return self::SUCCESS;
            }
            $created=0; $skipped=0; $stored=[];
            try {
                DB::transaction(function () use ($files,&$created,&$skipped,&$stored):void {
                    foreach ($files as $item) {
                        if (MuseumMedia::where('source_original_url',$item['original_url'])->exists()) {
                            $skipped++;continue;
                        }
                        $raw=file_get_contents($item['source_path']);
                        if (!is_string($raw))throw new RuntimeException('Cannot read original');
                        $info=@getimagesizefromstring($raw);
                        if (!$info || !in_array($info[2],[IMAGETYPE_JPEG,IMAGETYPE_PNG,IMAGETYPE_WEBP],true)) {
                            throw new RuntimeException('Image MIME/header invalid: '.$item['cms_slug']);
                        }
                        [$width,$height]=$info;
                        if ($width<1||$height<1||$width>7000||$height>7000||$width*$height>25_000_000) {
                            $this->warn('Source exceeds safe decoding limits; original safely archived: '.$item['cms_slug']);
                            $skipped++;continue;
                        }
                        $source=@imagecreatefromstring($raw);
                        if ($source===false) throw new RuntimeException('Image decoder refused original');
                        if (!imageistruecolor($source) && !imagepalettetotruecolor($source)) {
                            imagedestroy($source); throw new RuntimeException('Cannot safely convert original palette');
                        }
                        // Only the PRIVATE CMS preview is scaled, never the
                        // immutable original JPEG bytes. Preserve aspect ratio,
                        // all visible content and safe existing media limits.
                        $scale=min(1.0,4096/$width,4096/$height,
                            sqrt(16_000_000/($width*$height)));
                        if ($scale<1.0) {
                            $newWidth=max(1,(int)floor($width*$scale));
                            $newHeight=max(1,(int)floor($height*$scale));
                            $previewSurface=imagecreatetruecolor($newWidth,$newHeight);
                            imagealphablending($previewSurface,false);
                            imagesavealpha($previewSurface,true);
                            if(!imagecopyresampled($previewSurface,$source,0,0,0,0,
                                $newWidth,$newHeight,$width,$height)) {
                                imagedestroy($previewSurface);imagedestroy($source);
                                throw new RuntimeException('Cannot create proportional source preview');
                            }
                            imagedestroy($source);
                            $source=$previewSurface;
                            [$width,$height]=[$newWidth,$newHeight];
                        }
                        ob_start();
                        $ok=imagewebp($source,null,82);
                        $preview=ob_get_clean();
                        imagedestroy($source);
                        if (!$ok||!is_string($preview)||strlen($preview)>5_242_880) {
                            $this->warn('WebP CMS preview too large; original remains securely archived: '.$item['cms_slug']);
                            $skipped++;continue;
                        }
                        $alt=trim((string)$item['source_alt']);
                        if ($alt===''||MuseumAltPolicy::issue($alt)) {
                            // The original title is factual source metadata,
                            // NOT an invented account of what objects appear.
                            // Source rights remain embargoed and alt needs review.
                            $alt=mb_substr(trim((string)$item['title']),0,MuseumAltPolicy::MAX_LENGTH);
                        }
                        if (MuseumAltPolicy::issue($alt)) {
                            $this->warn('Museum image needs human alt caption; original preserved: '.$item['cms_slug']);
                            $skipped++;continue;
                        }
                        $digest=hash('sha256',$preview);
                        $target='museum/media/official-source/'.$digest.'.webp';
                        // One actual photograph is reused at TWO distinct
                        // official museum URLs on two separate excursions.
                        // Preserve both authentic editorial associations
                        // instead of silently omitting the second image.
                        if (MuseumMedia::where('storage_path',$target)->exists()) {
                            $target='museum/media/official-source/'
                                .$item['cms_slug'].'-'.$digest.'.webp';
                        }
                        if (Storage::disk('local')->exists($target)) {
                            if (!hash_equals($digest,hash_file('sha256',
                                Storage::disk('local')->path($target)))) {
                                throw new RuntimeException('Original CMS preview mismatch');
                            }
                        } else {
                            if(!Storage::disk('local')->put($target,$preview)) {
                                throw new RuntimeException('Cannot store private original preview');
                            }
                            $stored[]=$target;
                        }
                        MuseumMedia::create([
                            'museum_entry_id'=>$item['entry']->id,
                            'storage_path'=>$target,
                            'sha256'=>$digest,
                            'alt'=>$alt,
                            'caption'=>mb_substr((string)$item['title'],0,255),
                            'mime'=>'image/webp',
                            'width'=>$width,'height'=>$height,
                            'size_bytes'=>strlen($preview),
                            'source_rights_pending'=>true,
                            'source_original_url'=>$item['original_url'],
                            'source_original_sha256'=>$item['sha256'],
                        ]);
                        $created++;
                    }
                });
            } catch(Throwable $ex) {
                Storage::disk('local')->delete($stored);
                throw $ex;
            }
            $this->info("Added $created verified museum source photo previews as PRIVATE CMS media,"
                ." skipped $skipped; original JPEG/PNG/WebP files unchanged on SSD."
                ." No rights inferred or public export.");
            return self::SUCCESS;
        } catch(Throwable $ex) {
            $this->error('Original-photo import safely blocked: '.$ex->getMessage());
            return self::FAILURE;
        }
    }
}
