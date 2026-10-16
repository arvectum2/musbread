<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::table('museum_entries', static fn (Blueprint $table) => $table->dateTime('unpublish_at')->nullable());
        Schema::table('museum_events', static fn (Blueprint $table) => $table->dateTime('unpublish_at')->nullable());
    }

    public function down(): void
    {
        Schema::table('museum_events', static fn (Blueprint $table) => $table->dropColumn('unpublish_at'));
        Schema::table('museum_entries', static fn (Blueprint $table) => $table->dropColumn('unpublish_at'));
    }
};
