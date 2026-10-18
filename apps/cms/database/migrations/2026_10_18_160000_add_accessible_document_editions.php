<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::table('museum_documents', static function (Blueprint $table): void {
            // Private, not necessarily legally equivalent, until separately
            // reviewed by authorized museum editorial staff and bound to PDF SHA.
            $table->longText('accessible_html')->nullable();
            $table->string('accessible_edition_sha256',64)->nullable();
            $table->timestamp('accessible_reviewed_at')->nullable();
            $table->foreignId('accessible_reviewed_by')->nullable();
        });
    }
    public function down(): void
    {
        Schema::table('museum_documents', static function (Blueprint $table): void {
            $table->dropColumn([
                'accessible_html', 'accessible_edition_sha256',
                'accessible_reviewed_at', 'accessible_reviewed_by',
            ]);
        });
    }
};
