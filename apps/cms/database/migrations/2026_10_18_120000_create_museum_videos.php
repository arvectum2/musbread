<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up():void {
        Schema::create('museum_videos',static function(Blueprint $table):void {
            $table->id();
            $table->foreignId('museum_entry_id')->constrained('museum_entries')->restrictOnDelete();
            $table->string('code',80);
            $table->string('title',255);
            $table->text('embed_url');
            $table->text('source_url');
            $table->text('transcript');
            $table->boolean('rights_confirmed')->default(false);
            $table->string('status',16)->default('draft');
            $table->timestamps();
            $table->unique(['museum_entry_id','code']);
            $table->index(['museum_entry_id','status']);
        });
    }
    public function down():void { Schema::dropIfExists('museum_videos'); }
};
