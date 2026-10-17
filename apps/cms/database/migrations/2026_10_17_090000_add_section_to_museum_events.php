<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/** Existing events remain unassigned and accessible to administrators only. */
return new class extends Migration {
    public function up(): void
    {
        Schema::table('museum_events', static function (Blueprint $table): void {
            $table->foreignId('museum_section_id')->nullable()
                ->constrained('museum_sections')->restrictOnDelete();
        });
    }

    public function down(): void
    {
        Schema::table('museum_events', static function (Blueprint $table): void {
            $table->dropConstrainedForeignId('museum_section_id');
        });
    }
};
