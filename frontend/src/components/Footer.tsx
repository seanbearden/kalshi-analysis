import { motion } from 'framer-motion'
import { Github, Twitter, Linkedin } from 'lucide-react'

export function Footer() {
  const currentYear = new Date().getFullYear()

  const socialLinks = [
    { icon: Github, href: 'https://github.com/seanbearden', label: 'GitHub' },
    { icon: Twitter, href: 'https://twitter.com', label: 'Twitter' },
    { icon: Linkedin, href: 'https://linkedin.com', label: 'LinkedIn' },
  ]

  return (
    <footer className="border-t border-border/40 bg-muted/30 mt-16">
      <div className="container mx-auto px-4 py-8">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          {/* Left: Project Info */}
          <div className="text-center md:text-left">
            <p className="text-sm font-medium text-foreground">Kalshi Market Insights</p>
            <p className="text-xs text-muted-foreground mt-1">
              Portfolio demonstration project · Not a production trading tool
            </p>
          </div>

          {/* Center: Social Links */}
          <div className="flex items-center space-x-4">
            {socialLinks.map((link) => {
              const Icon = link.icon
              return (
                <motion.a
                  key={link.label}
                  href={link.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  whileHover={{ scale: 1.1, y: -2 }}
                  whileTap={{ scale: 0.95 }}
                  className="flex h-9 w-9 items-center justify-center rounded-lg bg-background border border-border/40 text-muted-foreground hover:text-foreground hover:border-border transition-colors"
                  aria-label={link.label}
                >
                  <Icon className="h-4 w-4" />
                </motion.a>
              )
            })}
          </div>

          {/* Right: Copyright */}
          <div className="text-center md:text-right">
            <p className="text-xs text-muted-foreground">
              © {currentYear} Sean Bearden. All rights reserved.
            </p>
          </div>
        </div>
      </div>
    </footer>
  )
}
