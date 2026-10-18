<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::table('museum_media', static function (Blueprint $table): void {
            // True for source-migrated photos until a separate rights review.
            // Ordinary approved editor-created media remains unchanged.
            $table->boolean('source_rights_pending')->default(false);
            $table->string('source_original_url', 600)->nullable();
            $table->string('source_original_sha256', 64)->nullable();
        });
    }

    public function down(): void
    {
        Schema::table('museum_media', static function (Blueprint $table): void {
            $table->dropColumn([
                'source_rights_pending', 'source_original_url', 'source_original_sha256',
            ]);
        });
    }
};
