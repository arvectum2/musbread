<?php
declare(strict_types=1);
namespace App\Http\Controllers;

use App\Models\MuseumEntry;
use App\Models\MuseumEvent;
use App\Support\MuseumEntryPublicationState;
use App\Support\MuseumInternalLinkInspector;
use App\Support\MuseumSectionAccess;
use Illuminate\Http\Response;

/**
 * Private, read-only editorial link picker for visual CMS editor.
 * Every URL is recomputed from the SAME eligibility conditions as exporter:
 * time window, approved ancestors, title+body for optional EN.
 * Draft titles and secrets never enter the page.
 */
final class MuseumContextLinksController extends Controller
{
    public function index(): Response
    {
        if (MuseumSectionAccess::user() === null) abort(403);
        $sectionIds = MuseumEntryPublicationState::publishedSectionIds();
        $publishedSection = static fn($query) => $query
            ->whereNull('museum_section_id')
            ->when($sectionIds !== [],
                static fn($q) => $q->orWhereIn('museum_section_id', $sectionIds));
        $types = array_flip(MuseumInternalLinkInspector::entryPrefixes());
        $entries = MuseumEntry::query()->public()->where($publishedSection)
            ->orderBy('type')->orderBy('title')->get(['type','slug','title',
                'title_en','body_en','museum_section_id'])
            ->filter(static fn($entry) => isset($types[$entry->type])
                && preg_match('/^[a-z0-9]+(?:-[a-z0-9]+)*$/D', $entry->slug))
            ->flatMap(static function($entry) use ($types):array {
                $uri='/'.$types[$entry->type].'/'.$entry->slug.'/';
                $result=[['title'=>$entry->title,'url'=>$uri,'type'=>$entry->type]];
                if (trim((string)$entry->title_en)!==''
                    && trim((string)$entry->body_en)!=='')
                    $result[]=['title'=>$entry->title_en,
                        'url'=>'/en'.$uri,'type'=>$entry->type.' (EN)'];
                return $result;
            });
        $events = MuseumEvent::query()->public()->where($publishedSection)
            ->orderBy('title')->get(['title','slug'])
            ->filter(static fn($event) => preg_match('/^[a-z0-9]+(?:-[a-z0-9]+)*$/D', $event->slug))
            ->map(static fn($event)=>['title'=>$event->title,
                'url'=>'/events/'.$event->slug.'/','type'=>'event']);
        $rows=$entries->concat($events)->values();
        return response()->view('entries.context-links',['links'=>$rows],200,[
            'Cache-Control'=>'private, no-store, max-age=0',
            'X-Robots-Tag'=>'noindex, nofollow, noarchive',
            'X-Content-Type-Options'=>'nosniff',
            'X-Frame-Options'=>'DENY',
            'Referrer-Policy'=>'no-referrer',
            'Content-Security-Policy'=>"default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
        ]);
    }
}
