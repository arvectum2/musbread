<?php

namespace Tests\Feature;

use App\Models\MuseumDocument;
use App\Models\MuseumEntry;
use App\Models\MuseumSection;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Storage;
use MoonShine\Laravel\Models\MoonshineUser;
use MoonShine\Laravel\Models\MoonshineUserRole;
use Tests\TestCase;
use ZipArchive;

class MuseumDocumentsTest extends TestCase
{
    use RefreshDatabase;

    private function entry(string $slug, string $status = 'draft', ?int $sectionId = null): MuseumEntry
    {
        return MuseumEntry::create([
            'type' => 'document', 'slug' => $slug, 'title' => 'Тестовый документ',
            'body' => '<p>Доступная HTML-альтернатива файла.</p>',
            'status' => $status, 'museum_section_id' => $sectionId,
        ]);
    }

    private function pdf(): UploadedFile
    {
        return UploadedFile::fake()->createWithContent('notice.pdf', "%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<<>>\n%%EOF\n");
    }

    private function office(string $format, bool $macro = false): UploadedFile
    {
        $path = tempnam(sys_get_temp_dir(), 'musbread-office');
        $zip = new ZipArchive();
        $zip->open($path, ZipArchive::OVERWRITE);
        $zip->addFromString('[Content_Types].xml', '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/></Types>');
        $zip->addFromString($format === 'docx' ? 'word/document.xml' : 'xl/workbook.xml', '<document/>');
        if ($macro) $zip->addFromString('word/vbaProject.bin', 'evil');
        $zip->close();
        $data = file_get_contents($path);
        @unlink($path);
        return UploadedFile::fake()->createWithContent('notice.'.$format, $data);
    }

    private function upload(int $entryId, UploadedFile $file)
    {
        return $this->post('/admin/museum-documents', [
            'museum_entry_id' => $entryId,
            'label' => 'Доступное название музейного документа',
            'document' => $file,
        ]);
    }

    public function test_anonymous_users_cannot_upload_or_download_documents(): void
    {
        $entry = $this->entry('anon-test');
        $this->get('/admin/museum-documents')->assertRedirect('/admin/login');
        $this->upload($entry->id, $this->pdf())->assertRedirect('/admin/login');
        $this->assertDatabaseCount('museum_documents', 0);
    }

    public function test_pdf_docx_xlsx_are_private_with_hash_and_force_attachment_download(): void
    {
        Storage::fake('local');
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        foreach (['pdf', 'docx', 'xlsx'] as $format) {
            $entry = $this->entry('doc-'.$format);
            $file = $format === 'pdf' ? $this->pdf() : $this->office($format);
            $this->upload($entry->id, $file)->assertRedirect(route('museum.documents.index'));
            $document = MuseumDocument::where('museum_entry_id', $entry->id)->firstOrFail();
            $this->assertSame($format, $document->file_type);
            $this->assertSame(hash('sha256', Storage::disk('local')->get($document->storage_path)), $document->sha256);
            $this->assertStringStartsWith('museum/documents/', $document->storage_path);
            $this->get(route('museum.documents.download', $document))
                ->assertOk()->assertHeader('Content-Type', 'application/octet-stream')
                ->assertHeader('X-Content-Type-Options', 'nosniff')
                ->assertHeader('Cache-Control', 'no-store, private');
        }
        $this->assertDatabaseCount('museum_documents', 3);
    }

    public function test_invalid_scripts_bogus_pdf_macros_and_legacy_xls_are_rejected(): void
    {
        Storage::fake('local');
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        $entry = $this->entry('invalid-file');
        $this->upload($entry->id, UploadedFile::fake()->createWithContent('evil.pdf', '<html><script>alert(1)</script></html>'))->assertSessionHasErrors('document');
        $this->upload($entry->id, UploadedFile::fake()->createWithContent('script.pdf', "%PDF-1.4\n1 0 obj\n<< /JavaScript (danger) >>\nendobj\n%%EOF"))->assertSessionHasErrors('document');
        $this->upload($entry->id, $this->office('docx', true))->assertSessionHasErrors('document');
        $this->upload($entry->id, UploadedFile::fake()->createWithContent('old.xls', "\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"."legacy OLE2"))
            ->assertSessionHasErrors('document');
        $this->upload($entry->id, UploadedFile::fake()->createWithContent('script.svg', '<svg><script>alert(1)</script></svg>'))->assertSessionHasErrors('document');
        $this->assertDatabaseCount('museum_documents', 0);
    }

    public function test_editor_has_no_permission_to_upload_or_fetch_other_section_documents(): void
    {
        Storage::fake('local');
        $one = MuseumSection::create(['slug' => 'one', 'title' => 'Один', 'status' => 'published']);
        $two = MuseumSection::create(['slug' => 'two', 'title' => 'Другой', 'status' => 'published']);
        $mine = $this->entry('mine', 'draft', $one->id);
        $other = $this->entry('other', 'draft', $two->id);
        $editorRole = MoonshineUserRole::where('name', 'Editor')->firstOrFail();
        $editor = MoonshineUser::factory()->create(['moonshine_user_role_id' => $editorRole->id]);
        $one->editors()->attach($editor->id);

        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        $this->upload($other->id, $this->pdf())->assertRedirect();
        $document = MuseumDocument::firstOrFail();

        $this->actingAs($editor, 'moonshine');
        $this->get('/admin/museum-documents')->assertOk()->assertDontSee($other->slug);
        $this->upload($mine->id, $this->pdf())->assertRedirect();
        $this->upload($other->id, $this->pdf())->assertForbidden();
        $this->get(route('museum.documents.download', $document))->assertForbidden();
        $this->delete(route('museum.documents.destroy', $document))->assertForbidden();
        $this->assertDatabaseCount('museum_documents', 2);
    }

    public function test_only_published_documents_enter_verified_snapshot_then_disappear_on_unpublish(): void
    {
        Storage::fake('local');
        $published = $this->entry('public-document', 'published');
        $private = $this->entry('private-document');
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        $this->upload($published->id, $this->pdf())->assertRedirect();
        $this->upload($private->id, $this->office('docx'))->assertRedirect();
        $one = MuseumDocument::where('museum_entry_id', $published->id)->firstOrFail();
        $other = MuseumDocument::where('museum_entry_id', $private->id)->firstOrFail();
        $dir = storage_path('framework/testing/documents-export-'.uniqid());
        $out = storage_path('framework/testing/documents-snapshot.json');
        $manifest = storage_path('framework/testing/documents-manifest.json');
        try {
            $args = [
                '--output' => $out,
                '--manifest' => $manifest,
                '--document-output-dir' => $dir,
                '--media-output-dir' => storage_path('framework/testing/unused-media-'.uniqid()),
            ];
            $this->artisan('museum:export', $args)->assertSuccessful();
            $snapshot = json_decode(file_get_contents($out), true, flags: JSON_THROW_ON_ERROR);
            $this->assertSame(['public-document'], array_column($snapshot['entries'], 'slug'));
            $this->assertCount(1, $snapshot['entries'][0]['documents']);
            $doc = $snapshot['entries'][0]['documents'][0];
            $this->assertSame('pdf', $doc['format']);
            $this->assertSame('Доступное название музейного документа', $doc['label']);
            $this->assertSame('/documents/'.$one->sha256.'.pdf', $doc['href']);
            $audit = json_decode(file_get_contents($manifest), true, flags: JSON_THROW_ON_ERROR);
            $this->assertSame($one->sha256, $audit['files']['documents/'.$one->sha256.'.pdf']['sha256']);
            $this->assertFileExists($dir.'/'.$one->sha256.'.pdf');
            $this->assertFileDoesNotExist($dir.'/'.$other->sha256.'.docx');
            $this->assertStringNotContainsString($one->storage_path, file_get_contents($out));

            $published->update(['status' => 'draft']);
            $this->artisan('museum:export', $args)->assertSuccessful();
            $this->assertFileDoesNotExist($dir.'/'.$one->sha256.'.pdf');
            $this->assertCount(0, json_decode(file_get_contents($out), true)['entries']);
        } finally {
            @unlink($out);
            @unlink($manifest);
            foreach (glob($dir.'/*') ?: [] as $file) @unlink($file);
            @rmdir($dir);
        }
    }

    public function test_modified_document_fails_closed_during_export_and_download(): void
    {
        Storage::fake('local');
        $entry = $this->entry('document-tamper', 'published');
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        $this->upload($entry->id, $this->pdf())->assertRedirect();
        $document = MuseumDocument::firstOrFail();
        Storage::disk('local')->put($document->storage_path, 'TAMPERED');
        $this->get(route('museum.documents.download', $document))->assertNotFound();
        $out = storage_path('framework/testing/tamper-document-snapshot.json');
        try {
            $this->expectException(\RuntimeException::class);
            $this->artisan('museum:export', ['--output' => $out]);
        } finally {
            @unlink($out);
        }
    }

    public function test_file_deletion_and_article_with_attached_files_protected(): void
    {
        Storage::fake('local');
        $entry = $this->entry('deletion');
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        $this->upload($entry->id, $this->pdf())->assertRedirect();
        $document = MuseumDocument::firstOrFail();
        try {
            $entry->delete();
            $this->fail('An entry with documents must not disappear silently');
        } catch (\Illuminate\Validation\ValidationException $exception) {
            $this->assertArrayHasKey('documents', $exception->errors());
        }
        $this->delete(route('museum.documents.destroy', $document))->assertRedirect();
        Storage::disk('local')->assertMissing($document->storage_path);
        $entry->delete();
        $this->assertDatabaseCount('museum_documents', 0);
    }
}
