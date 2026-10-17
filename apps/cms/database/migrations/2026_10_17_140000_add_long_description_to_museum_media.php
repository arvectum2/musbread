<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::table('museum_media', static function (Blueprint $table): void {
            $table->text('long_description')->nullable();
        });
    }

    public function down(): void
    {
        Schema::table('museum_media', static function (Blueprint $table): void {
            $table->dropColumn('long_description');
        });
    }
};
