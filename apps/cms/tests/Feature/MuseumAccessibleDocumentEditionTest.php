<?php

declare(strict_types=1);

namespace Tests\Feature;

use App\Models\MuseumDocument;
use App\Models\MuseumEntry;
use App\Support\MuseumDocumentAccessibleEdition;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\Storage;
use MoonShine\Laravel\Models\MoonshineUser;
use Tests\TestCase;

final class MuseumAccessibleDocumentEditionTest extends TestCase
{
    use RefreshDatabase;

    private function setupDocument(): MuseumDocument
    {
        Storage::fake('local');
        $entry=MuseumEntry::create([
            'type'=>'document',
            'slug'=>'qa-accessible-pdf',
            'title'=>'Синтетический PDF для проверки HTML',
            'body'=>'<p>Полная альтернатива будет согласована отдельно.</p>',
            'status'=>'published',
            'published_at'=>now()->subHour(),
        ]);
        $this->actingAs(MoonshineUser::factory()->create(),'moonshine');
        $this->post(route('museum.documents.store'),[
            'museum_entry_id'=>$entry->id,
            'label'=>'QA: синтетический документ',
            'document'=>UploadedFile::fake()->createWithContent('test.pdf',
                "%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<<>>\n%%EOF\n"),
        ])->assertRedirect();
        return MuseumDocument::firstOrFail();
    }

    private function sampleHtml():string
    {
        return '<h2>Синтетическая HTML-редакция для QA</h2>'
            .'<p>'.str_repeat('Это только искусственный текст для автоматического теста; он не заменяет ни один реальный официальный документ музея. ',5).'</p>'
            .'<table><caption>Таблица синтетических показателей</caption>'
            .'<thead><tr><th id="qa-indicator" scope="col">Показатель</th>'
            .'<th scope="col">Результат</th></tr></thead>'
            .'<tbody><tr><td headers="qa-indicator">Только QA</td><td>Тест</td></tr></tbody></table>';
    }

    private function review(MuseumDocument $doc,bool $approve,string $html,?string $sha=null)
    {
        return $this->patch(route('museum.documents.accessible-edition',$doc),[
            'source_sha256'=>$sha ?? $doc->sha256,
            'accessible_html'=>$html,
            'approve_equivalence'=>$approve?1:0,
        ]);
    }

    private function export(string $suffix):array
    {
        $name=storage_path('framework/testing/qa-equivalent-'.$suffix);
        $args=[
            '--output'=>$name.'.json',
            '--manifest'=>$name.'.manifest.json',
            '--document-output-dir'=>$name.'-documents',
            '--media-output-dir'=>$name.'-media',
        ];
        $code=1;
        try {$code=Artisan::call('museum:export',$args);}
        catch(\RuntimeException) {$code=1;}
        $result=is_file($name.'.json')
            ?json_decode((string)file_get_contents($name.'.json'),true):null;
        @unlink($name.'.json');@unlink($name.'.manifest.json');
        foreach (['documents','media'] as $kind) {
            foreach(glob($name.'-'.$kind.'/*')?:[] as $file)@unlink($file);
            @rmdir($name.'-'.$kind);
        }
        return [$code,$result];
    }

    public function test_approved_html_is_source_bound_and_only_exported_after_independent_editor_review():void
    {
        $doc=$this->setupDocument();
        $html=$this->sampleHtml();
        $this->review($doc,false,$html.'<script>alert("XSS")</script>')->assertRedirect();
        $this->assertNull($doc->fresh()->accessible_edition_sha256);
        $this->assertStringNotContainsString('<script',$doc->fresh()->accessible_html);
        [$status,$export]=$this->export('private-draft');
        $this->assertSame(0,$status);
        $this->assertArrayNotHasKey('accessible_html',$export['entries'][0]['documents'][0]);

        $this->review($doc,true,$html)->assertRedirect();
        $this->assertNotNull($doc->fresh()->accessible_edition_sha256);
        $this->assertNotNull($doc->fresh()->accessible_reviewed_by);
        [$status,$export]=$this->export('published');
        $this->assertSame(0,$status);
        $published=$export['entries'][0]['documents'][0];
        $this->assertSame($doc->sha256.'.pdf',basename($published['href']));
        $this->assertStringContainsString('Синтетическая HTML-редакция',$published['accessible_html']);
        $this->assertStringContainsString('<table>',$published['accessible_html']);
        $this->assertStringContainsString('<caption>Таблица синтетических показателей</caption>',$published['accessible_html']);
        $this->assertStringContainsString('scope="col"',$published['accessible_html']);
        $this->assertStringContainsString('headers="qa-indicator"',$published['accessible_html']);
        $this->assertArrayNotHasKey('accessible_edition_sha256',$published);
        $this->assertArrayNotHasKey('accessible_reviewed_by',$published);

        // A direct privileged metadata update still MUST invalidate export
        // even if an older approval signature remains set in the database.
        $doc->update(['accessible_html'=>'<p>'.str_repeat('Подмена ',70).'</p>']);
        [$status,$export]=$this->export('modified-after-approval');
        $this->assertSame(1,$status);
        $this->assertNull($export);
        $this->review($doc,false,$html)->assertRedirect();
        $this->assertNull($doc->fresh()->accessible_edition_sha256);
        [$status,$export]=$this->export('withdrawn');
        $this->assertSame(0,$status);
        $this->assertArrayNotHasKey('accessible_html',$export['entries'][0]['documents'][0]);
    }

    public function test_source_digest_mismatch_blocks_review_without_writing():void
    {
        $doc=$this->setupDocument();
        $this->review($doc,true,$this->sampleHtml(),str_repeat('0',64))
            ->assertSessionHasErrors('source_sha256');
        $this->assertNull($doc->fresh()->accessible_html);
        $this->assertNull($doc->fresh()->accessible_edition_sha256);
    }

    public function test_short_annotation_cannot_be_misrepresented_as_full_equivalent():void
    {
        $doc=$this->setupDocument();
        $this->review($doc,true,'<p>Аннотация: две строки.</p>')
            ->assertSessionHasErrors('accessible_html');
        $this->assertNull($doc->fresh()->accessible_edition_sha256);
    }

    public function test_unsigned_user_cannot_publish_html_from_cms():void
    {
        $doc=$this->setupDocument();
        auth('moonshine')->logout();
        $this->review($doc,true,$this->sampleHtml())
            ->assertRedirect('/admin/login');
        $this->assertNull($doc->fresh()->accessible_html);
    }

    public function test_editing_one_accessible_document_revisions_requires_new_approval():void
    {
        $doc=$this->setupDocument();
        $before=\App\Support\MuseumApprovalRevision::fingerprint($doc->entry);
        $this->review($doc,true,$this->sampleHtml())->assertRedirect();
        $this->assertNotSame($before,
            \App\Support\MuseumApprovalRevision::fingerprint($doc->entry));
        $edition=app(MuseumDocumentAccessibleEdition::class);
        $this->assertSame($edition->signature($doc->sha256,$doc->fresh()->accessible_html),
            $doc->fresh()->accessible_edition_sha256);
    }
}
