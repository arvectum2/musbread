<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::table('museum_content_approvals', static function (Blueprint $table): void {
            $table->unsignedBigInteger('museum_entry_id')->nullable()->change();
            $table->unsignedBigInteger('museum_event_id')->nullable();
            $table->unsignedBigInteger('museum_section_id')->nullable();
            $table->unique(['museum_event_id', 'revision_sha256'], 'museum_event_revision_unique');
            $table->unique(['museum_section_id', 'revision_sha256'], 'museum_section_revision_unique');
        });
    }
    public function down(): void
    {
        Schema::table('museum_content_approvals', static function (Blueprint $table): void {
            $table->dropUnique('museum_event_revision_unique');
            $table->dropUnique('museum_section_revision_unique');
            $table->dropColumn(['museum_event_id', 'museum_section_id']);
            $table->unsignedBigInteger('museum_entry_id')->nullable(false)->change();
        });
    }
};
