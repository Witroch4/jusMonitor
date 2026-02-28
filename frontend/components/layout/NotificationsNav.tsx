'use client'

import { cn } from "@/lib/utils"

export function NotificationsNav() {
    return (
        <button className="relative p-2 rounded-full hover:bg-muted transition-colors">
            <span className="material-symbols-outlined text-muted-foreground hover:text-primary cursor-pointer transition-colors text-2xl">
                notifications
            </span>
            <span className="absolute top-2 right-2 w-2 h-2 bg-destructive rounded-full border-2 border-background"></span>
        </button>
    )
}
