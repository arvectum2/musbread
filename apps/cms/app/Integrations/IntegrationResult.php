<?php

namespace App\Integrations;

final readonly class IntegrationResult
{
    private function __construct(
        public string $status,
        public string $message,
        public ?string $reference = null,
    ) {}

    public static function disabled(): self
    {
        return new self('disabled', 'Интеграция не подключена: запросите согласованный способ у музея.');
    }

    public static function mock(IntegrationKind $kind): self
    {
        return new self('mock', 'Демонстрационный ответ, реальная операция не выполнена.', 'MOCK-'.$kind->value);
    }

    public static function failure(): self
    {
        return new self('error', 'Внешний сервис недоступен; не считать операцию выполненной.');
    }

    public static function timeout(): self
    {
        return new self('timeout', 'Истекло время ожидания. Статус операции неизвестен; не повторяйте её автоматически.');
    }
}
