<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::create('museum_editorial_task_updates', static function (Blueprint $table): void {
            $table->id();
            $table->string('baseline_sha256', 64);
            $table->string('candidate_sha256', 64);
            $table->string('item_group', 16);
            $table->string('item_key', 200);
            $table->string('task_status', 20);
            $table->string('priority', 12);
            $table->unsignedBigInteger('assignee_id');
            $table->unsignedBigInteger('actor_id');
            $table->text('note');
            $table->timestamp('created_at')->useCurrent();
            $table->index(['baseline_sha256','candidate_sha256','item_group'], 'museum_task_snapshot_idx');
        });
    }
    public function down(): void { Schema::dropIfExists('museum_editorial_task_updates'); }
};
