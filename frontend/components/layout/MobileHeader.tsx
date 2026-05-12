'use client'

import { Menu } from 'lucide-react'
import { useState } from 'react'
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Sidebar } from './Sidebar'

export function MobileHeader() {
  const [open, setOpen] = useState(false)
  return (
    <header className="flex h-14 items-center gap-3 border-b border-border bg-background px-4 md:hidden">
      <Sheet open={open} onOpenChange={(isOpen) => setOpen(isOpen)}>
        <SheetTrigger
          render={
            <Button variant="ghost" size="icon" className="h-8 w-8" aria-label="Open navigation">
              <Menu className="h-4 w-4" />
            </Button>
          }
        />
        <SheetContent side="left" className="w-60 p-0">
          <Sidebar />
        </SheetContent>
      </Sheet>
      <span className="text-sm font-semibold">FilingsIQ</span>
    </header>
  )
}
