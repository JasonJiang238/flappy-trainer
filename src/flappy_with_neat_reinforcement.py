import pygame
from pygame.locals import *
import random
import neat
import os

pygame.init()

clock = pygame.time.Clock()
fps = 60

screen_width = 864
screen_height = 936

screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption('Flappy Bird AI')

font = pygame.font.SysFont('Bauhaus 93', 60)
white = (255, 255, 255)

ground_scroll = 0
scroll_speed = 4
pipe_gap = 150
pipe_frequency = 1500

bg = pygame.image.load('src/img/bg.png')
ground_img = pygame.image.load('src/img/ground.png')

generation = 0


def draw_text(text, font, text_col, x, y):
	img = font.render(text, True, text_col)
	screen.blit(img, (x, y))


class Bird(pygame.sprite.Sprite):
	def __init__(self, x, y):
		pygame.sprite.Sprite.__init__(self)
		self.images = []
		self.index = 0
		self.counter = 0
		for num in range(1, 4):
			img = pygame.image.load(f"src/img/bird{num}.png")
			self.images.append(img)
		self.image = self.images[self.index]
		self.rect = self.image.get_rect()
		self.rect.center = [x, y]
		self.vel = 0

	def update(self):
		# Apply gravity
		self.vel += 0.5
		if self.vel > 8:
			self.vel = 8
		if self.rect.bottom < 768:
			self.rect.y += int(self.vel)

		# Animation
		self.counter += 1
		if self.counter > 5:
			self.counter = 0
			self.index += 1
			if self.index >= len(self.images):
				self.index = 0
			self.image = self.images[self.index]

		# Rotate bird
		self.image = pygame.transform.rotate(self.images[self.index], self.vel * -2)

	def jump(self):
		self.vel = -10


class Pipe(pygame.sprite.Sprite):
	def __init__(self, x, y, position):
		pygame.sprite.Sprite.__init__(self)
		self.image = pygame.image.load("src/img/pipe.png")
		self.rect = self.image.get_rect()
		
		if position == 1:
			self.image = pygame.transform.flip(self.image, False, True)
			self.rect.bottomleft = [x, y - int(pipe_gap / 2)]
		elif position == -1:
			self.rect.topleft = [x, y + int(pipe_gap / 2)]

	def update(self):
		self.rect.x -= scroll_speed
		if self.rect.right < 0:
			self.kill()


# NEAT runs this function every generation
def run_game(genomes, config):
	global generation
	generation += 1
	
	# Create birds and neural networks for each genome
	birds = []
	nets = []
	ge = []
	
	for genome_id, genome in genomes:
		# Start fitness at 0
		genome.fitness = 0
		
		# Create neural network from genome
		net = neat.nn.FeedForwardNetwork.create(genome, config)
		nets.append(net)
		
		# Create bird
		birds.append(Bird(100, screen_height // 2))
		ge.append(genome)
	
	# Game variables
	pipes = pygame.sprite.Group()
	ground_scroll = 0
	last_pipe = pygame.time.get_ticks() - pipe_frequency
	score = 0
	
	run = True
	while run and len(birds) > 0:
		clock.tick(fps)
		
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				run = False
				pygame.quit()
				quit()
		
		# Find which pipe to look at
		pipe_index = 0
		if len(birds) > 0:
			if len(pipes) > 1 and birds[0].rect.x > list(pipes)[0].rect.x + 70:
				pipe_index = 1
		
		# Update each bird
		for i, bird in enumerate(birds):
			bird.update()
			ge[i].fitness += 0.1  # Small reward for staying alive
			
			# Get inputs for neural network
			pipe_list = list(pipes)
			if len(pipe_list) > 0:
				# Input 1: Bird Y position
				# Input 2: Distance to top pipe
				# Input 3: Distance to bottom pipe
				output = nets[i].activate((
					bird.rect.y,
					abs(bird.rect.y - pipe_list[pipe_index].rect.top),
					abs(bird.rect.y - pipe_list[pipe_index].rect.bottom)
				))
				
				# If output > 0.5, jump
				if output[0] > 0.5:
					bird.jump()
		
		# Generate new pipes
		time_now = pygame.time.get_ticks()
		if time_now - last_pipe > pipe_frequency:
			pipe_height = random.randint(-100, 100)
			btm_pipe = Pipe(screen_width, screen_height // 2 + pipe_height, -1)
			top_pipe = Pipe(screen_width, screen_height // 2 + pipe_height, 1)
			pipes.add(btm_pipe, top_pipe)
			last_pipe = time_now
		
		# Update pipes
		pipes.update()
		
		# Remove birds that hit pipes or go out of bounds
		for pipe in pipes:
			for i, bird in enumerate(birds):
				if pipe.rect.colliderect(bird.rect):
					ge[i].fitness -= 1  # Penalty for hitting pipe
					birds.pop(i)
					nets.pop(i)
					ge.pop(i)
					break
			
			# Check if passed pipe
			if not hasattr(pipe, 'passed'):
				pipe.passed = False
			if pipe.rect.right < 100 and not pipe.passed:
				pipe.passed = True
				score += 1
				# Reward all alive birds
				for g in ge:
					g.fitness += 5
		
		# Remove birds that hit ground or ceiling
		for i, bird in enumerate(birds):
			if bird.rect.top <= 0 or bird.rect.bottom >= 768:
				birds.pop(i)
				nets.pop(i)
				ge.pop(i)
		
		# Scroll ground
		ground_scroll -= scroll_speed
		if abs(ground_scroll) > 35:
			ground_scroll = 0
		
		# Draw everything
		screen.blit(bg, (0, 0))
		pipes.draw(screen)
		for bird in birds:
			screen.blit(bird.image, bird.rect)
		screen.blit(ground_img, (ground_scroll, 768))
		
		# Display info
		draw_text(f'Score: {score}', font, white, 10, 10)
		draw_text(f'Gen: {generation}', font, white, 10, 70)
		draw_text(f'Alive: {len(birds)}', font, white, 10, 130)
		
		pygame.display.update()


# Run NEAT
def run_neat(config_path):
	config = neat.config.Config(
		neat.DefaultGenome,
		neat.DefaultReproduction,
		neat.DefaultSpeciesSet,
		neat.DefaultStagnation,
		config_path
	)
	
	# Create population of 50 birds
	p = neat.Population(config)
	
	# Show stats in console
	p.add_reporter(neat.StdOutReporter(True))
	stats = neat.StatisticsReporter()
	p.add_reporter(stats)
	
	# Run for 50 generations
	winner = p.run(run_game, 50)


if __name__ == '__main__':
	
	config_path = "C:\\Users\\ragha\\Downloads\\My git folder 2\\flappy-trainer\\src\\config-neat.txt"
	run_neat(config_path)