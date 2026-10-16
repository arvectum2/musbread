<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('museum_entry_relations', static function (Blueprint $table): void {
            $table->id();
            $table->foreignId('source_entry_id')->constrained('museum_entries')->cascadeOnDelete();
            $table->foreignId('target_entry_id')->constrained('museum_entries')->cascadeOnDelete();
            $table->unique(['source_entry_id', 'target_entry_id']);
        });
        Schema::create('museum_entry_events', static function (Blueprint $table): void {
            $table->id();
            $table->foreignId('museum_entry_id')->constrained('museum_entries')->cascadeOnDelete();
            $table->foreignId('museum_event_id')->constrained('museum_events')->cascadeOnDelete();
            $table->unique(['museum_entry_id', 'museum_event_id']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('museum_entry_events');
        Schema::dropIfExists('museum_entry_relations');
    }
};
