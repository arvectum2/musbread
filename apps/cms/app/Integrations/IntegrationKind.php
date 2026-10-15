<?php

namespace App\Integrations;

/** Integration needs stated in the museum specification, not provider brands. */
enum IntegrationKind: string
{
    case Ticketing = 'tickets';
    case ExcursionBooking = 'excursion_booking';
    case Maps = 'maps';
    case Analytics = 'analytics';
    case Social = 'social';
    case Video = 'video';
    case Feedback = 'feedback';
}
