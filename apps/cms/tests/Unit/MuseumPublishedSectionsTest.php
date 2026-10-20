<?php

namespace Tests\Unit;

use App\Models\MuseumSection;
use App\Support\MuseumPublishedSections;
use Illuminate\Database\Eloquent\Collection as ModelCollection;
use PHPUnit\Framework\TestCase;

class MuseumPublishedSectionsTest extends TestCase
{
    private function section(int $id, string $status, ?int $parent = null): MuseumSection
    {
        $section = new MuseumSection();
        $section->setRawAttributes(['id' => $id, 'parent_id' => $parent, 'status' => $status], true);
        return $section;
    }

    public function test_only_published_ancestors_admit_public_sections(): void
    {
        $input = new ModelCollection([
            $this->section(1, 'published'),
            $this->section(2, 'published', 1),
            $this->section(3, 'draft'),
            $this->section(4, 'published', 3),
            $this->section(5, 'published', 42),
            $this->section(6, 'published', 7),
            $this->section(7, 'published', 6),
            $this->section(8, 'published', 2),
        ]);
        $this->assertSame([1, 2, 8], MuseumPublishedSections::filter($input)->values()->modelKeys());
        $this->assertCount(8, $input, 'Private records must not be removed or mutated');
    }

    public function test_empty_tree_remains_empty_and_late_draft_hides_descendants(): void
    {
        $this->assertSame([], MuseumPublishedSections::filter(new ModelCollection())->all());
        $tree = new ModelCollection([$this->section(1, 'draft'), $this->section(2, 'published', 1)]);
        $this->assertSame([], MuseumPublishedSections::filter($tree)->modelKeys());
    }
}
