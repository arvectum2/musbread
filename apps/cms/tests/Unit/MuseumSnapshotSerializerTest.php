<?php

namespace Tests\Unit;

use App\Support\MuseumSnapshotSerializer;
use JsonException;
use PHPUnit\Framework\TestCase;

class MuseumSnapshotSerializerTest extends TestCase
{
    private MuseumSnapshotSerializer $serializer;

    protected function setUp(): void
    {
        parent::setUp();
        $this->serializer = new MuseumSnapshotSerializer();
    }

    public function test_byte_stable_unicode_json_matches_canonical_v1_and_keeps_array_order(): void
    {
        $content = ['z' => [['last' => 'второй'], ['first' => 'первый']], 'a' => 'Музей / Хлеба'];
        $copy = $content;
        $this->assertSame(
            "{\"a\":\"Музей / Хлеба\",\"z\":[{\"last\":\"второй\"},{\"first\":\"первый\"}]}\n",
            $this->serializer->encode($content)
        );
        $this->assertSame($copy, $content, 'Do not mutate published CMS inputs');
    }

    public function test_manifest_contains_only_public_files_and_matching_exact_payload_digest(): void
    {
        $payload = $this->serializer->encode(['schema_version' => 1, 'entries' => []]);
        $media = ['media/'.str_repeat('a', 64).'.webp' => ['sha256' => str_repeat('a', 64), 'bytes' => 39]];
        $manifest = $this->serializer->manifest($payload, $media, [], 0, 0, null);
        $result = json_decode($manifest, true, flags: JSON_THROW_ON_ERROR);

        $this->assertSame(hash('sha256', $payload), $result['files']['published.json']['sha256']);
        $this->assertSame(strlen($payload), $result['files']['published.json']['bytes']);
        $actual = $result['files']['media/'.str_repeat('a', 64).'.webp'];
        $this->assertSame(str_repeat('a', 64), $actual['sha256']);
        $this->assertSame(39, $actual['bytes']);
        $this->assertArrayNotHasKey('section_count', $result, 'Legacy fixture schema must remain unchanged');
        $this->assertSame(1, $result['schema_version']);
        $this->assertSame($manifest, $this->serializer->manifest($payload, $media, [], 0, 0, null));
    }

    public function test_explicit_section_count_and_document_manifest_remain_compatible(): void
    {
        $payload = "{}\n";
        $doc = ['documents/'.str_repeat('b', 64).'.pdf' => ['sha256' => str_repeat('b', 64), 'bytes' => 20]];
        $result = json_decode($this->serializer->manifest($payload, [], $doc, 2, 4, 0), true, flags: JSON_THROW_ON_ERROR);
        $this->assertSame(0, $result['section_count']);
        $this->assertSame(2, $result['event_count']);
        $this->assertSame(4, $result['entry_count']);
        $this->assertCount(2, $result['files']);
    }

    public function test_invalid_utf8_fails_closed_instead_of_writing_corrupt_json(): void
    {
        $this->expectException(JsonException::class);
        $this->serializer->encode(['body' => "\xFF"]);
    }
}
