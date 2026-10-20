<?php

declare(strict_types=1);

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::table('museum_entries', function (Blueprint $table) {
            $table->unsignedBigInteger('edit_version')->default(0);
        });
    }

    public function down(): void
    {
        Schema::table('museum_entries', function (Blueprint $table) {
            $table->dropColumn('edit_version');
        });
    }
};
